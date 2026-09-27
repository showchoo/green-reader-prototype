package jp.example.greenreader.precision

import com.google.ar.core.Coordinates2d
import com.google.ar.core.Frame
import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.NotYetAvailableException
import jp.example.greenreader.analysis.GravityAlignedFrame
import java.nio.ByteOrder
import kotlin.math.max

class PrecisionDepthCollector(
    private val confidenceThreshold: Int = 128
) {
    private val samples = ArrayList<PrecisionDepthPoint>(70000)
    private val frameTimestamps = LinkedHashSet<Long>()
    private var lastRawTimestamp = Long.MIN_VALUE
    private var attemptedFrames = 0
    private var rawAcquiredFrames = 0
    private var rawNonZeroPixels = 0L
    private var confidencePassedPixels = 0L
    private var notYetAvailableCount = 0
    private var otherErrorCount = 0
    private var lastError = ""

    @Synchronized fun clear() {
        samples.clear()
        frameTimestamps.clear()
        lastRawTimestamp = Long.MIN_VALUE
        attemptedFrames = 0
        rawAcquiredFrames = 0
        rawNonZeroPixels = 0
        confidencePassedPixels = 0
        notYetAvailableCount = 0
        otherErrorCount = 0
        lastError = ""
    }

    @Synchronized fun size(): Int = samples.size
    @Synchronized fun uniqueFrames(): Int = frameTimestamps.size
    @Synchronized fun snapshot(): List<PrecisionDepthPoint> = samples.toList()
    @Synchronized fun diagnosticSummary(): String =
        "attempts=" + attemptedFrames +
        " rawFrames=" + rawAcquiredFrames +
        " nonZero=" + rawNonZeroPixels +
        " confPass=" + confidencePassedPixels +
        " acceptedFrames=" + frameTimestamps.size +
        " points=" + samples.size +
        " notYet=" + notYetAvailableCount +
        " errors=" + otherErrorCount +
        " lastError=" + (if (lastError.isBlank()) "-" else lastError)

    @Synchronized
    fun integrate(
        frame: Frame,
        referencePose: Pose,
        pixelStrideStep: Int = 4,
        minDepthM: Float = 0.25f,
        maxDepthM: Float = 5f
    ) {
        val camera = frame.camera
        if (camera.trackingState != TrackingState.TRACKING) return
        attemptedFrames++
        try {
            frame.acquireRawDepthImage16Bits().use { depth ->
                val timestamp = depth.timestamp
                rawAcquiredFrames++
                if (timestamp == lastRawTimestamp) return
                frame.acquireRawDepthConfidenceImage().use { confidence ->
                    lastRawTimestamp = timestamp
                    val dp = depth.planes[0]
                    val cp = confidence.planes[0]
                    val db = dp.buffer.order(ByteOrder.LITTLE_ENDIAN)
                    val cb = cp.buffer
                    val intr = camera.imageIntrinsics
                    val focal = intr.focalLength
                    val principal = intr.principalPoint
                    val dims = intr.imageDimensions
                    val step = max(2, pixelStrideStep)
                    val capacity = ((depth.width + step - 1) / step) * ((depth.height + step - 1) / step)
                    val tex = FloatArray(capacity * 2)
                    val zs = FloatArray(capacity)
                    val confs = FloatArray(capacity)
                    var count = 0

                    for (y in 0 until depth.height step step) {
                        for (x in 0 until depth.width step step) {
                            val di = y * dp.rowStride + x * dp.pixelStride
                            if (di + 1 >= db.limit()) continue
                            val mm = java.lang.Short.toUnsignedInt(db.getShort(di))
                            if (mm == 0) continue
                            rawNonZeroPixels++
                            val z = mm / 1000f
                            if (z !in minDepthM..maxDepthM) continue

                            val cx = (x * confidence.width / depth.width).coerceIn(0, confidence.width - 1)
                            val cy = (y * confidence.height / depth.height).coerceIn(0, confidence.height - 1)
                            val ci = cy * cp.rowStride + cx * cp.pixelStride
                            if (ci >= cb.limit()) continue
                            val conf = cb.get(ci).toInt() and 0xff
                            if (conf < confidenceThreshold) continue
                            confidencePassedPixels++

                            val o = count * 2
                            tex[o] = (x + 0.5f) / depth.width.toFloat()
                            tex[o + 1] = (y + 0.5f) / depth.height.toFloat()
                            zs[count] = z
                            confs[count] = conf / 255f
                            count++
                        }
                    }
                    if (count == 0) return@use

                    val image = FloatArray(count * 2)
                    frame.transformCoordinates2d(
                        Coordinates2d.TEXTURE_NORMALIZED,
                        tex.copyOf(count * 2),
                        Coordinates2d.IMAGE_PIXELS,
                        image
                    )
                    val levelFrame = GravityAlignedFrame.fromPose(referencePose)
                    for (i in 0 until count) {
                        val u = image[i * 2]
                        val v = image[i * 2 + 1]
                        if (!u.isFinite() || !v.isFinite()) continue
                        if (u < 0f || v < 0f || u >= dims[0] || v >= dims[1]) continue
                        val z = zs[i]
                        val xCam = (u - principal[0]) / focal[0] * z
                        val yCam = -(v - principal[1]) / focal[1] * z
                        val world = camera.pose.transformPoint(floatArrayOf(xCam, yCam, -z))
                        val local = levelFrame.worldToLocal(world)
                        samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp)
                    }
                    frameTimestamps += timestamp
                    if (samples.size > 90000) samples.subList(0, samples.size - 70000).clear()
                }
            }
        } catch (_: NotYetAvailableException) {
            notYetAvailableCount++
            lastError = "NotYetAvailable"
        } catch (t: Throwable) {
            otherErrorCount++
            lastError = t.javaClass.simpleName + ":" + (t.message ?: "")
        }
    }
}
