from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

old='''                // IMPORTANT: use the ORIGINAL tapped ray, not the neighboring sample
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
'''
new='''                // Use the ORIGINAL tapped ray, but reconstruct it with the same
                // Full Depth mapping used by depthPointAtTap() and PrecisionDepthCollector.
                // Depth image coordinates are TEXTURE_NORMALIZED; map them to CPU
                // IMAGE_PIXELS before applying imageIntrinsics.
                val imageCoord = FloatArray(2)
                frame.transformCoordinates2d(
                    Coordinates2d.TEXTURE_NORMALIZED,
                    floatArrayOf(tx, ty),
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
    raise SystemExit("v4.2 target missing: ball neighbor depth unprojection")
s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")
print("Applied Precision v4.2 aligned ball Depth fallback")
