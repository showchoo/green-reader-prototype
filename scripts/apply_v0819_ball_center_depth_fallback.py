from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.19 pattern not found ({label}):\n{old[:1800]}")
    s = s.replace(old, new, 1)

# Keep the field-confirmed v0.8.18/v0.8.7 geometry completely unchanged. Only the
# first Ball mark gets a fallback when every existing exact Depth/Plane/DepthPoint
# lookup fails. A white golf ball can make a small hole in ARCore Depth. Instead of
# moving the mark to a neighboring pixel, borrow only the surrounding green's depth
# and unproject that depth through the ORIGINAL tapped screen ray. This keeps the
# ball/cup lateral geometry identical to the user's tap.
old_mark_resolve = '''        val p = try {
            resolveMarkPoint(f, x, y)
        } catch (_: Throwable) {
            null
        }
        if (p != null) {
            applyMark(mode, p)
            return
        }
'''
new_mark_resolve = '''        var p = try {
            resolveMarkPoint(f, x, y)
        } catch (_: Throwable) {
            null
        }
        if (p == null && mode == 1) {
            p = try {
                ballPointFromNeighborDepth(f, x, y)
            } catch (_: Throwable) {
                null
            }
        }
        if (p != null) {
            applyMark(mode, p)
            return
        }
'''
replace_once(old_mark_resolve, new_mark_resolve, "ball-only borrowed-depth fallback")

helper = r'''
    /**
     * Ball-only fallback for a Depth hole on the white ball.
     *
     * The neighboring pixels are used ONLY to estimate z. The x/y ray stays the
     * exact original tap, so this fallback cannot move the Ball mark left or right
     * and therefore does not alter the field-confirmed v0.8.7 direction mapping.
     */
    private fun ballPointFromNeighborDepth(frame: Frame, x: Float, y: Float): Vec3? {
        if (viewportW <= 1 || viewportH <= 1) return null
        return try {
            frame.acquireDepthImage16Bits().use { img ->
                val inCoords = floatArrayOf(
                    (x / viewportW).coerceIn(0f, 1f),
                    (y / viewportH).coerceIn(0f, 1f)
                )
                val texCoords = FloatArray(2)
                frame.transformCoordinates2d(
                    Coordinates2d.VIEW_NORMALIZED,
                    inCoords,
                    Coordinates2d.TEXTURE_NORMALIZED,
                    texCoords
                )
                if (!texCoords[0].isFinite() || !texCoords[1].isFinite()) return null

                val tx = texCoords[0].coerceIn(0f, 0.9999f)
                val ty = texCoords[1].coerceIn(0f, 0.9999f)
                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                val plane = img.planes[0]
                val buf = plane.buffer.order(ByteOrder.LITTLE_ENDIAN)

                // depthPointAtTap() already searched radius 0..4. Search only the
                // surrounding green, nearest ring first. Stop as soon as one ring
                // has enough coherent samples.
                val values = ArrayList<Int>(160)
                var found = false
                for (radius in 5..12) {
                    values.clear()
                    val outer2 = radius * radius
                    val inner = kotlin.math.max(4, radius - 3)
                    val inner2 = inner * inner
                    for (dy in -radius..radius) {
                        for (dx in -radius..radius) {
                            val d2 = dx * dx + dy * dy
                            if (d2 > outer2 || d2 < inner2) continue
                            val xx = px + dx
                            val yy = py + dy
                            if (xx !in 0 until img.width || yy !in 0 until img.height) continue
                            val idx = yy * plane.rowStride + xx * plane.pixelStride
                            if (idx + 1 >= buf.limit()) continue
                            val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                            if (mm in 200..12000) values += mm
                        }
                    }
                    if (values.size >= 10) {
                        found = true
                        break
                    }
                }
                if (!found || values.size < 6) return null

                // Reject a mixed foreground/background ring. The putting surface
                // around one ball should form one tight depth cluster.
                values.sort()
                val median = values[values.size / 2]
                val toleranceMm = kotlin.math.max(80, (median * 0.05f).toInt())
                val clustered = values.filter { kotlin.math.abs(it - median) <= toleranceMm }
                if (clustered.size < 6) return null
                val z = clustered[clustered.size / 2] / 1000f

                // IMPORTANT: use the ORIGINAL tapped ray, not the neighboring sample
                // coordinates. This is intentionally the same v0.8.7 unprojection
                // convention used by depthPointAtTap().
                val intr = frame.camera.textureIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val u = tx * dims[0]
                val v = ty * dims[1]
                val cx = (u - principal[0]) / focal[0] * z
                val cy = -(v - principal[1]) / focal[1] * z
                val world = frame.camera.pose.transformPoint(floatArrayOf(cx, cy, -z))
                Vec3(world[0], world[1], world[2])
            }
        } catch (_: NotYetAvailableException) {
            null
        } catch (_: Throwable) {
            null
        }
    }

'''
marker = "    private fun analyzeGrain() {\n"
if marker not in s:
    raise SystemExit("v0.8.19 analyzeGrain insertion point not found")
s = s.replace(marker, helper + marker, 1)

# On a cold app start, Ball is the only mark attempted before AR tracking/depth has
# had time to settle. Hold the very first Ball prompt for a short TRACKING warm-up.
# This is never repeated after the session has warmed, so Reset remains immediate.
replace_once(
    "    private var markMode = 1\n",
    """    private var markMode = 0
    private var initialBallMarkReady = false
    private var initialTrackingStartedMs = 0L
""",
    "initial Ball warm-up state",
)

replace_once(
    '            text = "ボールをタップしてください"\n',
    '            text = "AR準備中… 端末をゆっくり動かしてください"\n',
    "initial warm-up status",
)

warmup_call_target = '''            bg.draw(f)

            // Failed marks are single-shot. Never resolve an old screen x/y on a
'''
warmup_call_replacement = '''            bg.draw(f)
            maybeUnlockInitialBallMark(f)

            // Failed marks are single-shot. Never resolve an old screen x/y on a
'''
replace_once(warmup_call_target, warmup_call_replacement, "renderer warm-up call")

warmup_helper = r'''
    private fun maybeUnlockInitialBallMark(frame: Frame) {
        if (initialBallMarkReady || ball != null) return
        if (frame.camera.trackingState != TrackingState.TRACKING) {
            initialTrackingStartedMs = 0L
            return
        }
        val now = SystemClock.elapsedRealtime()
        if (initialTrackingStartedMs == 0L) initialTrackingStartedMs = now
        if (now - initialTrackingStartedMs < 700L) return

        initialBallMarkReady = true
        runOnUiThread {
            if (ball == null && markMode == 0) {
                markMode = 1
                status.text = "ボールをタップしてください"
            }
        }
    }

'''
mark_marker = "    private fun markAt(x: Float, y: Float) {\n"
if mark_marker not in s:
    raise SystemExit("v0.8.19 markAt insertion point not found")
s = s.replace(mark_marker, warmup_helper + mark_marker, 1)

# Reset is immediate once this app session has warmed. If Reset happens during the
# first 700 ms, keep waiting rather than inviting a Ball tap that is likely to fail.
reset_start = s.find("    private fun resetAll() {")
reset_end = s.find("    private fun showMap()", reset_start)
if reset_start < 0 or reset_end < 0:
    raise SystemExit("v0.8.19 resetAll boundaries not found")
reset = s[reset_start:reset_end]
reset = reset.replace(
    "        markMode = 1\n",
    "        markMode = if (initialBallMarkReady) 1 else 0\n",
    1,
)
reset = reset.replace(
    '        status.text = "ボールをタップしてください"\n',
    '        status.text = if (initialBallMarkReady) "ボールをタップしてください" else "AR準備中… 端末をゆっくり動かしてください"\n',
    1,
)
s = s[:reset_start] + reset + s[reset_end:]

if 'appVersion = "0.8.18"' not in s:
    raise SystemExit("v0.8.19 appVersion target not found")
s = s.replace('appVersion = "0.8.18"', 'appVersion = "0.8.19"', 1)

# Safety assertions: this patch must not touch any slope/overlay/consensus direction
# math. It is strictly Ball acquisition + cold-start readiness.
if "ballPointFromNeighborDepth(f, x, y)" not in s:
    raise SystemExit("v0.8.19 Ball fallback missing")
if "maybeUnlockInitialBallMark(f)" not in s:
    raise SystemExit("v0.8.19 initial warm-up missing")
if "SlopeConsensus.combine(consensusReports, minAgree = 4)" not in s:
    raise SystemExit("v0.8.19 v0.8.18 consensus unexpectedly changed")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.19 Ball-center borrowed-depth fallback + cold-start warm-up")
