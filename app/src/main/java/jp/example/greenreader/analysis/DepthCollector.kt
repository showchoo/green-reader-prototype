package jp.example.greenreader.analysis

import com.google.ar.core.Coordinates2d
import com.google.ar.core.Frame
import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.NotYetAvailableException
import java.nio.ByteOrder
import kotlin.math.max

class DepthCollector {
    private val points = ArrayList<Vec3>(30000)

    @Synchronized fun clear() = points.clear()
    @Synchronized fun size(): Int = points.size
    @Synchronized fun snapshot(): List<Vec3> = points.toList()

    /**
     * Integrate depth into a persistent reference frame.
     *
     * ARCore may adjust its world coordinate space as tracking improves. Raw world
     * coordinates from different frames therefore must not be accumulated directly.
     * [referencePose] is the current pose of the ball Anchor; converting every depth
     * point through its inverse keeps all samples in the same physical, anchor-local
     * coordinate frame across the entire scan.
     *
     * Depth image pixels are in ARCore's depth/texture coordinate space, not simply a
     * resized camera texture. Convert depth TEXTURE_NORMALIZED coordinates to CPU
     * IMAGE_PIXELS with Frame.transformCoordinates2d(), then unproject with
     * Camera.imageIntrinsics. This accounts for crop/orientation and prevents a
     * mirrored or shifted lateral point cloud.
     */
    @Synchronized
    fun integrate(
        frame: Frame,
        referencePose: Pose,
        pixelStrideStep: Int = 6,
        minDepthM: Float = 0.25f,
        maxDepthM: Float = 8f
    ) {
        val camera = frame.camera
        if (camera.trackingState != TrackingState.TRACKING) return
        try {
            frame.acquireDepthImage16Bits().use { img ->
                val plane = img.planes[0]
                val buf = plane.buffer.order(ByteOrder.LITTLE_ENDIAN)
                val pStride = plane.pixelStride
                val rStride = plane.rowStride
                val intr = camera.imageIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val cameraPose = camera.pose
                val worldToReference = referencePose.inverse()

                val step = max(2, pixelStrideStep)
                val sampleCapacity = ((img.width + step - 1) / step) * ((img.height + step - 1) / step)
                val textureCoords = FloatArray(sampleCapacity * 2)
                val depths = FloatArray(sampleCapacity)
                var sampleCount = 0

                for (y in 0 until img.height step step) {
                    for (x in 0 until img.width step step) {
                        val idx = y * rStride + x * pStride
                        if (idx + 1 >= buf.limit()) continue
                        val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                        if (mm == 0) continue
                        val z = mm / 1000f
                        if (z < minDepthM || z > maxDepthM) continue

                        val out = sampleCount * 2
                        textureCoords[out] = (x + 0.5f) / img.width.toFloat()
                        textureCoords[out + 1] = (y + 0.5f) / img.height.toFloat()
                        depths[sampleCount] = z
                        sampleCount++
                    }
                }

                if (sampleCount == 0) return@use

                val usedTextureCoords = textureCoords.copyOf(sampleCount * 2)
                val imageCoords = FloatArray(sampleCount * 2)
                frame.transformCoordinates2d(
                    Coordinates2d.TEXTURE_NORMALIZED,
                    usedTextureCoords,
                    Coordinates2d.IMAGE_PIXELS,
                    imageCoords
                )

                val imageW = dims[0].toFloat()
                val imageH = dims[1].toFloat()
                for (i in 0 until sampleCount) {
                    val u = imageCoords[i * 2]
                    val v = imageCoords[i * 2 + 1]
                    if (!u.isFinite() || !v.isFinite()) continue
                    if (u < 0f || v < 0f || u >= imageW || v >= imageH) continue

                    val z = depths[i]
                    val cx = (u - principal[0]) / focal[0] * z
                    val cy = -(v - principal[1]) / focal[1] * z
                    val world = cameraPose.transformPoint(floatArrayOf(cx, cy, -z))
                    val local = worldToReference.transformPoint(world)
                    points += Vec3(local[0], local[1], local[2])
                }

                if (points.size > 70000) {
                    points.subList(0, points.size - 50000).clear()
                }
            }
        } catch (_: NotYetAvailableException) {
        }
    }
}
