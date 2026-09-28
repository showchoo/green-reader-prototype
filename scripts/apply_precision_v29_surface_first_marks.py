from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

old='''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return depthPointAtTap(frame, x, y)
            ?: exactSurfaceHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }
'''
new='''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        // Prefer ARCore tracked physical surfaces. Depth is only a fallback:
        // Full Depth may contain completed/background geometry along the tap ray.
        return exactSurfaceHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
            ?: depthPointAtTap(frame, x, y)
    }
'''
if old not in s:
    raise SystemExit("v4.3 target missing: resolveMarkPoint")
s=s.replace(old,new,1)

# Tighten mark hit distance to reject far background surfaces.
s=s.replace(
    'return d2.isFinite() && d2 >= 0.04f && d2 <= 25.0f',
    'return d2.isFinite() && d2 >= 0.04f && d2 <= 16.0f',
    1
)

# Tighten ball borrowed-depth fallback from 12 m to 4 m.
s=s.replace('if (mm in 200..12000) values += mm','if (mm in 200..4000) values += mm')
s=s.replace('val z = clustered[clustered.size / 2] / 1000f','val z = clustered[clustered.size / 2] / 1000f\n                if (z > 4.0f) return null',1)

p.write_text(s,encoding="utf-8")
print("Applied Precision v4.3 surface-first fail-closed marking")
