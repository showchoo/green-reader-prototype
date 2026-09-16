from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")

# Replace tap-depth unprojection with the same ARCore coordinate conversion used by
# DepthCollector. A depth pixel is in TEXTURE_NORMALIZED space; convert it to CPU
# IMAGE_PIXELS before applying Camera.imageIntrinsics. This accounts for crop and
# orientation instead of assuming the depth map is a simple resized texture.
start = s.find("    private fun depthPointAtTap(frame: Frame, x: Float, y: Float): Vec3? {")
end = s.find("    private fun analyzeGrain()", start)
if start < 0 or end < 0:
    raise SystemExit("v0.8.14 depthPointAtTap boundaries not found")

new_depth = r'''    private fun depthPointAtTap(frame: Frame, x: Float, y: Float): Vec3? {
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
                if (texCoords[0] < 0f || texCoords[1] < 0f) return null

                val tx = texCoords[0].coerceIn(0f, 0.9999f)
                val ty = texCoords[1].coerceIn(0f, 0.9999f)
                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                val plane = img.planes[0]
                val buf = plane.buffer.order(ByteOrder.LITTLE_ENDIAN)

                var bestX = -1
                var bestY = -1
                var bestMm = 0
                var bestD2 = Int.MAX_VALUE
                for (radius in listOf(0, 1, 2, 3, 4)) {
                    for (dy in -radius..radius) {
                        for (dx in -radius..radius) {
                            if (radius > 0 && kotlin.math.max(kotlin.math.abs(dx), kotlin.math.abs(dy)) != radius) continue
                            val xx = (px + dx).coerceIn(0, img.width - 1)
                            val yy = (py + dy).coerceIn(0, img.height - 1)
                            val idx = yy * plane.rowStride + xx * plane.pixelStride
                            if (idx + 1 >= buf.limit()) continue
                            val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                            if (mm !in 200..12000) continue
                            val d2 = dx * dx + dy * dy
                            if (d2 < bestD2) {
                                bestD2 = d2
                                bestX = xx
                                bestY = yy
                                bestMm = mm
                            }
                        }
                    }
                    if (bestX >= 0) break
                }
                if (bestX < 0) return null

                val values = ArrayList<Int>(25)
                for (dy in -2..2) for (dx in -2..2) {
                    val xx = (bestX + dx).coerceIn(0, img.width - 1)
                    val yy = (bestY + dy).coerceIn(0, img.height - 1)
                    val idx = yy * plane.rowStride + xx * plane.pixelStride
                    if (idx + 1 < buf.limit()) {
                        val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                        if (mm in 200..12000) values += mm
                    }
                }
                val z = if (values.isNotEmpty()) {
                    values.sort()
                    values[values.size / 2] / 1000f
                } else bestMm / 1000f

                // ARCore's documented depth-image mapping: depth coordinates are
                // TEXTURE_NORMALIZED. Convert to CPU IMAGE_PIXELS, then unproject
                // using imageIntrinsics. Do not use textureIntrinsics here.
                val depthCoord = floatArrayOf(
                    (bestX + 0.5f) / img.width.toFloat(),
                    (bestY + 0.5f) / img.height.toFloat()
                )
                val imageCoord = FloatArray(2)
                frame.transformCoordinates2d(
                    Coordinates2d.TEXTURE_NORMALIZED,
                    depthCoord,
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
            }
        } catch (_: NotYetAvailableException) {
            null
        } catch (_: Throwable) {
            null
        }
    }

'''
s = s[:start] + new_depth + s[end:]

# A 3-vs-2 split is too weak for a directional field result. Only display a
# direction when at least four of the five short windows agree; otherwise ask for
# another scan instead of showing a possibly reversed arrow.
old_consensus = "        val combined = SlopeConsensus.combine(consensusReports)\n"
new_consensus = "        val combined = SlopeConsensus.combine(consensusReports, minAgree = 4)\n"
if old_consensus not in s:
    raise SystemExit("v0.8.14 consensus combine call not found")
s = s.replace(old_consensus, new_consensus, 1)

s = s.replace('appVersion = "0.8.13"', 'appVersion = "0.8.14"')

if "Coordinates2d.TEXTURE_NORMALIZED" not in new_depth or "camera.imageIntrinsics" not in new_depth:
    raise SystemExit("v0.8.14 ARCore depth coordinate conversion missing")
if "minAgree = 4" not in s:
    raise SystemExit("v0.8.14 strong consensus threshold missing")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.14 ARCore depth coordinate mapping and 4-of-5 consensus")
