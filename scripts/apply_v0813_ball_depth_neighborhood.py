from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.13 pattern not found ({label}):\n{old[:1600]}")
    s = s.replace(old, new, 1)


# A golf ball often occupies a tiny, bright/texture-poor patch where ARCore depth
# has a hole even though the surrounding green is valid. Cup marking happens later
# and has been reliable in field testing, so keep its exact-pixel behavior unchanged.
# For the first (ball) mark only, search a small same-frame neighbourhood before
# falling back to ARCore surface hit tests. No delayed retry and no later-frame x/y
# reuse is introduced, so the v0.8.7 arrow-coordinate fix remains untouched.
old_resolve = '''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return depthPointAtTap(frame, x, y)
            ?: exactSurfaceHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }
'''
new_resolve = '''    private fun resolveMarkPoint(
        frame: Frame,
        x: Float,
        y: Float,
        wideDepthSearch: Boolean = false
    ): Vec3? {
        return depthPointAtTap(frame, x, y)
            ?: if (wideDepthSearch) depthPointNearTap(frame, x, y) else null
            ?: exactSurfaceHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }

    private fun depthPointNearTap(frame: Frame, x: Float, y: Float): Vec3? {
        // Ordered nearest-first so the accepted 3D point stays as close as possible
        // to the ball centre while stepping around a missing depth pixel on the ball.
        val offsets = arrayOf(
            6f to 0f, -6f to 0f, 0f to 6f, 0f to -6f,
            6f to 6f, 6f to -6f, -6f to 6f, -6f to -6f,
            12f to 0f, -12f to 0f, 0f to 12f, 0f to -12f,
            12f to 12f, 12f to -12f, -12f to 12f, -12f to -12f,
            20f to 0f, -20f to 0f, 0f to 20f, 0f to -20f,
            28f to 0f, -28f to 0f, 0f to 28f, 0f to -28f
        )
        for ((dx, dy) in offsets) {
            val sx = (x + dx).coerceIn(1f, (viewportW - 2).coerceAtLeast(1).toFloat())
            val sy = (y + dy).coerceIn(1f, (viewportH - 2).coerceAtLeast(1).toFloat())
            val p = depthPointAtTap(frame, sx, sy)
            if (p != null) return p
        }
        return null
    }
'''
replace_once(old_resolve, new_resolve, "ball depth neighbourhood")

# v0.8.11 restored immediate single-frame marking. Widen only the ball's depth
# lookup; cup behavior remains exactly as before because it is already reliable.
mark_start = s.find("    private fun markAt(")
mark_end = s.find("    private fun resolveQueuedMark(", mark_start)
if mark_start < 0 or mark_end < 0:
    raise SystemExit("v0.8.13 markAt boundaries not found")
mark = s[mark_start:mark_end]
old_call = "            resolveMarkPoint(frame, x, y)\n"
new_call = "            resolveMarkPoint(frame, x, y, wideDepthSearch = mode == 1)\n"
if old_call not in mark:
    raise SystemExit("v0.8.13 immediate mark resolve call not found")
mark = mark.replace(old_call, new_call, 1)
s = s[:mark_start] + mark + s[mark_end:]

# Field logs identify the build that produced the measurement.
s = s.replace('appVersion = "0.8.12"', 'appVersion = "0.8.13"')

if "wideDepthSearch = mode == 1" not in s:
    raise SystemExit("v0.8.13 ball-only wide depth search missing")
if "private fun depthPointNearTap" not in s:
    raise SystemExit("v0.8.13 neighbourhood helper missing")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.13 ball depth neighbourhood fallback")
