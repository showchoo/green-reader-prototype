from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.0 pattern not found ({label}):\n{old[:500]}")
    s = s.replace(old, new, 1)

# The previous order trusted ARCore hitTest first. On a putting mat / green that can
# latch to a feature point or plane behind the intended pixel. That was visible as
# a 1.3 m putt being reported around 3.3 m; the wrong 3D ball/cup endpoints then
# define the wrong corridor and can invert the fitted cross-slope. Prefer the depth
# sample at the exact tapped pixel, which is the measurement we actually want.
replace_once(
    """    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return exactHitPoint(frame, x, y)
            ?: depthPointAtTap(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }
""",
    """    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return depthPointAtTap(frame, x, y)
            ?: exactSurfaceHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }
""",
    "resolve mark priority",
)

# Do not accept a generic visual feature Point as the primary exact hit. A Point
# may belong to background geometry along the same tap ray. Plane and DepthPoint
# are surface-constrained and are substantially safer fallbacks when depth is
# temporarily unavailable.
replace_once(
    """    private fun exactHitPoint(frame: Frame, x: Float, y: Float): Vec3? {
        val hit = frame.hitTest(x, y).firstOrNull { h ->
            val t = h.trackable
            (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
        } ?: return null
        val tr = hit.hitPose.translation
        return Vec3(tr[0], tr[1], tr[2])
    }
""",
    """    private fun exactSurfaceHitPoint(frame: Frame, x: Float, y: Float): Vec3? {
        val hit = frame.hitTest(x, y).firstOrNull { h ->
            val t = h.trackable
            (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint
        } ?: return null
        val tr = hit.hitPose.translation
        return Vec3(tr[0], tr[1], tr[2])
    }
""",
    "surface-only exact hit",
)

# Keep the broad nearby fallback for difficult frames, but prefer actual surfaces
# over generic feature points there too.
replace_once(
    """            val hit = frame.hitTest(sx, sy).firstOrNull { h ->
                val t = h.trackable
                (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
            }
""",
    """            val hit = frame.hitTest(sx, sy).firstOrNull { h ->
                val t = h.trackable
                (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint
            }
""",
    "surface-only nearby hit",
)

# Logs must identify the actual build used in field tests.
s = s.replace('appVersion = "0.7.7"', 'appVersion = BuildConfig.VERSION_NAME')

path.write_text(s, encoding="utf-8")
print("Applied v0.8.0 depth-first ball/cup marking")
