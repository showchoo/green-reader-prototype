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
    private var lastRequestedMaxDepthM = 5f

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
        lastRequestedMaxDepthM = 5f
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
        " maxDepth=" + String.format("%.2f", lastRequestedMaxDepthM) +
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
        lastRequestedMaxDepthM = maxDepthM
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

        // ARCore's official Raw Depth reconstruction uses texture intrinsics,
        // scaled directly to the acquired depth image dimensions.
        val intr = camera.textureIntrinsics
        val intrFocal = intr.focalLength
        val intrPrincipal = intr.principalPoint
        val intrDims = intr.imageDimensions
        val fx = intrFocal[0] * depth.width.toFloat() / intrDims[0].toFloat()
        val fy = intrFocal[1] * depth.height.toFloat() / intrDims[1].toFloat()
        val cx = intrPrincipal[0] * depth.width.toFloat() / intrDims[0].toFloat()
        val cy = intrPrincipal[1] * depth.height.toFloat() / intrDims[1].toFloat()

        val step = max(2, pixelStrideStep)
        val capacity = ((depth.width + step - 1) / step) * ((depth.height + step - 1) / step)
        val xs = IntArray(capacity)
        val ys = IntArray(capacity)
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
                if (isRaw) rawInRangePixels++ else fullInRangePixels++

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

                xs[count] = x
                ys[count] = y
                zs[count] = z
                confs[count] = confValue
                count++
            }
        }

        if (count == 0) return false

        val levelFrame = GravityAlignedFrame.fromPose(referencePose)
        var added = 0

        if (isRaw) {
            // Raw Depth: Google's Raw Depth sample reconstructs directly from
            // native depth pixels with texture intrinsics scaled to depth size.
            for (i in 0 until count) {
                val px = xs[i].toFloat()
                val py = ys[i].toFloat()
                val z = zs[i]
                if (!fx.isFinite() || !fy.isFinite() || fx <= 0f || fy <= 0f) continue
                transformedValidPoints++
                val xCam = z * (px - cx) / fx
                val yCam = z * (cy - py) / fy
                val world = camera.pose.transformPoint(floatArrayOf(xCam, yCam, -z))
                val local = levelFrame.worldToLocal(world)
                samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp)
                added++
            }
        } else {
            // Full Depth: the standard Depth API documents depth coordinates in
            // texture-normalized space and provides transformCoordinates2d() for
            // mapping them to CPU IMAGE_PIXELS. Reconstruct with imageIntrinsics.
            val tex = FloatArray(count * 2)
            for (i in 0 until count) {
                tex[i * 2] = (xs[i] + 0.5f) / depth.width.toFloat()
                tex[i * 2 + 1] = (ys[i] + 0.5f) / depth.height.toFloat()
            }
            val imagePixels = FloatArray(count * 2)
            frame.transformCoordinates2d(
                Coordinates2d.TEXTURE_NORMALIZED,
                tex,
                Coordinates2d.IMAGE_PIXELS,
                imagePixels
            )
            val imageIntr = camera.imageIntrinsics
            val imageFocal = imageIntr.focalLength
            val imagePrincipal = imageIntr.principalPoint
            val imageDims = imageIntr.imageDimensions
            for (i in 0 until count) {
                val u = imagePixels[i * 2]
                val v = imagePixels[i * 2 + 1]
                if (!u.isFinite() || !v.isFinite()) continue
                if (u < 0f || v < 0f || u >= imageDims[0].toFloat() || v >= imageDims[1].toFloat()) continue
                val z = zs[i]
                transformedValidPoints++
                val xCam = (u - imagePrincipal[0]) / imageFocal[0] * z
                val yCam = -(v - imagePrincipal[1]) / imageFocal[1] * z
                val world = camera.pose.transformPoint(floatArrayOf(xCam, yCam, -z))
                val local = levelFrame.worldToLocal(world)
                samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp)
                added++
            }
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
