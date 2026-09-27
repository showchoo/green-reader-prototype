from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Precision v3.5 target missing: {label}")
    s = s.replace(old, new, 1)

once(
'''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return exactHitPoint(frame, x, y)
            ?: depthPointAtTap(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }
''',
'''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        // Precision analysis must keep marks on the same physical Depth surface
        // as the accumulated point cloud. Prefer tapped Depth first; AR hit-test
        // anchors can occasionally resolve to a distant stale/incorrect feature.
        return depthPointAtTap(frame, x, y)
            ?: exactHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }

    private fun isPlausibleMarkHit(frame: Frame, pose: Pose): Boolean {
        val camera = frame.camera.pose.translation
        val p = pose.translation
        val dx = p[0] - camera[0]
        val dy = p[1] - camera[1]
        val dz = p[2] - camera[2]
        val d2 = dx * dx + dy * dy + dz * dz
        return d2.isFinite() && d2 >= 0.04f && d2 <= 25.0f
    }
''',
'depth-first mark resolution'
)

once(
'''        val hit = frame.hitTest(x, y).firstOrNull { h ->
            val t = h.trackable
            (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
        } ?: return null
''',
'''        val hit = frame.hitTest(x, y).firstOrNull { h ->
            val t = h.trackable
            val validType = (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
            validType && isPlausibleMarkHit(frame, h.hitPose)
        } ?: return null
''',
'exact hit distance gate'
)

once(
'''            val hit = frame.hitTest(sx, sy).firstOrNull { h ->
                val t = h.trackable
                (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
            }
''',
'''            val hit = frame.hitTest(sx, sy).firstOrNull { h ->
                val t = h.trackable
                val validType = (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
                validType && isPlausibleMarkHit(frame, h.hitPose)
            }
''',
'nearby hit distance gate'
)

p.write_text(s, encoding="utf-8")
print("Applied Precision v3.5 Depth-first mark alignment")
