package jp.example.greenreader.precision

import android.media.Image
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
    private var lastDepthTimestamp = Long.MIN_VALUE

    private var attemptedFrames = 0
    private var rawAcquiredFrames = 0
    private var rawNonZeroPixels = 0L
    private var confidencePassedPixels = 0L
    private var fullAcquiredFrames = 0
    private var fullNonZeroPixels = 0L
    private var rawInRangePixels = 0L
    private var fullInRangePixels = 0L
    private var fallbackFrames = 0
    private var transformedValidPoints = 0L
    private var notYetAvailableCount = 0
    private var otherErrorCount = 0
    private var lastError = ""

    @Synchronized fun clear() {
        samples.clear()
        frameTimestamps.clear()
        lastDepthTimestamp = Long.MIN_VALUE
        attemptedFrames = 0
        rawAcquiredFrames = 0
        rawNonZeroPixels = 0
        confidencePassedPixels = 0
        fullAcquiredFrames = 0
        fullNonZeroPixels = 0
        rawInRangePixels = 0
        fullInRangePixels = 0
        fallbackFrames = 0
        transformedValidPoints = 0
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
        " rawNonZero=" + rawNonZeroPixels +
        " confPass=" + confidencePassedPixels +
        " fullFrames=" + fullAcquiredFrames +
        " fullNonZero=" + fullNonZeroPixels +
        " rawInRange=" + rawInRangePixels +
        " fullInRange=" + fullInRangePixels +
        " fallbackFrames=" + fallbackFrames +
        " transformedValid=" + transformedValidPoints +
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

        var rawAccepted = false

        try {
            frame.acquireRawDepthImage16Bits().use { depth ->
                rawAcquiredFrames++
                frame.acquireRawDepthConfidenceImage().use { confidence ->
                    rawAccepted = integrateImage(
                        frame = frame,
                        referencePose = referencePose,
                        depth = depth,
                        confidence = confidence,
                        pixelStrideStep = pixelStrideStep,
                        minDepthM = minDepthM,
                        maxDepthM = maxDepthM,
                        isRaw = true
                    )
                }
            }
        } catch (_: NotYetAvailableException) {
            notYetAvailableCount++
            lastError = "RawNotYetAvailable"
        } catch (t: Throwable) {
            otherErrorCount++
            lastError = "Raw:" + t.javaClass.simpleName + ":" + (t.message ?: "")
        }

        if (rawAccepted) return

        try {
            frame.acquireDepthImage16Bits().use { depth ->
                fullAcquiredFrames++
                fallbackFrames++
                integrateImage(
                    frame = frame,
                    referencePose = referencePose,
                    depth = depth,
                    confidence = null,
                    pixelStrideStep = pixelStrideStep,
                    minDepthM = minDepthM,
                    maxDepthM = maxDepthM,
                    isRaw = false
                )
            }
        } catch (_: NotYetAvailableException) {
            notYetAvailableCount++
            lastError = "FullNotYetAvailable"
        } catch (t: Throwable) {
            otherErrorCount++
            lastError = "Full:" + t.javaClass.simpleName + ":" + (t.message ?: "")
        }
    }

    private fun integrateImage(
        frame: Frame,
        referencePose: Pose,
        depth: Image,
        confidence: Image?,
        pixelStrideStep: Int,
        minDepthM: Float,
        maxDepthM: Float,
        isRaw: Boolean
    ): Boolean {
        val timestamp = depth.timestamp
        if (timestamp == lastDepthTimestamp) return false

        val camera = frame.camera
        val dp = depth.planes[0]
        val db = dp.buffer.order(ByteOrder.nativeOrder())
        val cp = confidence?.planes?.getOrNull(0)
        val cb = cp?.buffer

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

                if (isRaw) rawNonZeroPixels++ else fullNonZeroPixels++

                val z = mm / 1000f
                if (z !in minDepthM..maxDepthM) continue

                val confValue = if (confidence != null && cp != null && cb != null) {
                    val cx = (x * confidence.width / depth.width).coerceIn(0, confidence.width - 1)
                    val cy = (y * confidence.height / depth.height).coerceIn(0, confidence.height - 1)
                    val ci = cy * cp.rowStride + cx * cp.pixelStride
                    if (ci >= cb.limit()) continue
                    val conf = cb.get(ci).toInt() and 0xff
                    if (conf < confidenceThreshold) continue
                    confidencePassedPixels++
                    conf / 255f
                } else {
                    // Full Depth is spatially completed and has no confidence image.
                    // Give it a moderate weight; temporal/voxel filters still decide stability.
                    0.65f
                }

                val o = count * 2
                tex[o] = (x + 0.5f) / depth.width.toFloat()
                tex[o + 1] = (y + 0.5f) / depth.height.toFloat()
                zs[count] = z
                confs[count] = confValue
                count++
            }
        }

        if (count == 0) return false

        // ARCore Depth coordinates are texture-normalized coordinates. Convert
        // directly to CPU camera IMAGE_PIXELS as documented by the Depth API.
        // Do not pass through IMAGE_NORMALIZED and rescale again; that produced
        // severely distorted 3D coordinates on the arrows We2.
        val imagePixels = FloatArray(count * 2)
        frame.transformCoordinates2d(
            Coordinates2d.TEXTURE_NORMALIZED,
            tex.copyOf(count * 2),
            Coordinates2d.IMAGE_PIXELS,
            imagePixels
        )

        val levelFrame = GravityAlignedFrame.fromPose(referencePose)
        var added = 0
        for (i in 0 until count) {
            val u = imagePixels[i * 2]
            val v = imagePixels[i * 2 + 1]
            if (!u.isFinite() || !v.isFinite()) continue
            if (u < 0f || v < 0f || u >= dims[0].toFloat() || v >= dims[1].toFloat()) continue
            transformedValidPoints++
            val z = zs[i]
            val xCam = (u - principal[0]) / focal[0] * z
            val yCam = -(v - principal[1]) / focal[1] * z
            val world = camera.pose.transformPoint(floatArrayOf(xCam, yCam, -z))
            val local = levelFrame.worldToLocal(world)
            samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp)
            added++
        }

        if (added > 0) {
            lastDepthTimestamp = timestamp
            frameTimestamps += timestamp
            if (samples.size > 90000) samples.subList(0, samples.size - 70000).clear()
            return true
        }
        return false
    }
}
