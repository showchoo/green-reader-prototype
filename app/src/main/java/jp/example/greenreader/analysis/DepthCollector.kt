package jp.example.greenreader.analysis

import com.google.ar.core.Frame
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.NotYetAvailableException
import java.nio.ByteOrder
import kotlin.math.max

class DepthCollector {
    private val points = ArrayList<Vec3>(30000)

    @Synchronized fun clear() = points.clear()
    @Synchronized fun size(): Int = points.size
    @Synchronized fun snapshot(): List<Vec3> = points.toList()

    @Synchronized
    fun integrate(frame: Frame, pixelStrideStep: Int = 6, minDepthM: Float = 0.25f, maxDepthM: Float = 8f) {
        val camera = frame.camera
        if (camera.trackingState != TrackingState.TRACKING) return
        try {
            frame.acquireDepthImage16Bits().use { img ->
                val plane = img.planes[0]
                val buf = plane.buffer.order(ByteOrder.LITTLE_ENDIAN)
                val pStride = plane.pixelStride
                val rStride = plane.rowStride
                val intr = camera.textureIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val texW = dims[0].toFloat()
                val texH = dims[1].toFloat()
                val pose = camera.pose

                val step = max(2, pixelStrideStep)
                for (y in 0 until img.height step step) {
                    for (x in 0 until img.width step step) {
                        val idx = y * rStride + x * pStride
                        if (idx + 1 >= buf.limit()) continue
                        val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                        if (mm == 0) continue
                        val z = mm / 1000f
                        if (z < minDepthM || z > maxDepthM) continue

                        val u = (x + 0.5f) / img.width * texW
                        val v = (y + 0.5f) / img.height * texH
                        val cx = (u - principal[0]) / focal[0] * z
                        val cy = -(v - principal[1]) / focal[1] * z
                        val world = pose.transformPoint(floatArrayOf(cx, cy, -z))
                        points += Vec3(world[0], world[1], world[2])
                    }
                }

                if (points.size > 70000) {
                    points.subList(0, points.size - 50000).clear()
                }
            }
        } catch (_: NotYetAvailableException) {
        }
    }
}
