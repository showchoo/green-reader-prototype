from pathlib import Path


p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")

old = '''                val intr = frame.camera.textureIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val sampleTx = (bestX + 0.5f) / img.width.toFloat()
                val sampleTy = (bestY + 0.5f) / img.height.toFloat()
                val u = sampleTx * dims[0]
                val v = sampleTy * dims[1]
                val cx = (u - principal[0]) / focal[0] * z
                val cy = -(v - principal[1]) / focal[1] * z
                val world = frame.camera.pose.transformPoint(floatArrayOf(cx, cy, -z))
                Vec3(world[0], world[1], world[2])
'''

new = '''                // acquireDepthImage16Bits() is Full Depth. Its pixels are in
                // TEXTURE_NORMALIZED space. Map to IMAGE_PIXELS before applying
                // imageIntrinsics, consistently with PrecisionDepthCollector and
                // ballPointFromNeighborDepth(). Device testing must still verify
                // the geometry; differing intrinsics alone do not prove an error.
                val imageCoord = FloatArray(2)
                frame.transformCoordinates2d(
                    Coordinates2d.TEXTURE_NORMALIZED,
                    floatArrayOf(
                        (bestX + 0.5f) / img.width.toFloat(),
                        (bestY + 0.5f) / img.height.toFloat()
                    ),
                    Coordinates2d.IMAGE_PIXELS,
                    imageCoord
                )
                val u = imageCoord[0]
                val v = imageCoord[1]
                val intr = frame.camera.imageIntrinsics
                val dims = intr.imageDimensions
                if (!u.isFinite() || !v.isFinite() ||
                    u < 0f || v < 0f || u >= dims[0].toFloat() || v >= dims[1].toFloat()) {
                    return null
                }
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val cx = (u - principal[0]) / focal[0] * z
                val cy = -(v - principal[1]) / focal[1] * z
                val world = frame.camera.pose.transformPoint(floatArrayOf(cx, cy, -z))
                Vec3(world[0], world[1], world[2])
'''

if old not in s:
    raise SystemExit("v5.5 target missing: Full Depth tap unprojection")
s = s.replace(old, new, 1)

if 'appVersion = "Precision 5.4"' not in s:
    raise SystemExit("v5.5 target missing: app version")
s = s.replace('appVersion = "Precision 5.4"', 'appVersion = "Precision 5.5"', 1)

p.write_text(s, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if 'versionName = "5.4"' not in g:
    raise SystemExit("v5.5 target missing: Gradle version")
if 'versionCode = 540' not in g:
    raise SystemExit("v5.5 target missing: Gradle version code")
g = g.replace('versionName = "5.4"', 'versionName = "5.5"', 1)
g = g.replace('versionCode = 540', 'versionCode = 550', 1)
gradle.write_text(g, encoding="utf-8")

print("Applied Precision v5.5 unified Full Depth image-intrinsics marker ray")
