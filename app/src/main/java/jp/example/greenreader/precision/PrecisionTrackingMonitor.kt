package jp.example.greenreader.precision

import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.sqrt

/**
 * Lightweight scan-time tracking health monitor.
 *
 * It does not treat normal user motion as drift. Instead it detects implausible
 * frame-to-frame pose jumps while also recording how much deliberate camera
 * motion was available for Depth-from-Motion.
 */
class PrecisionTrackingMonitor {
    data class Snapshot(
        val totalFrames: Int = 0,
        val trackingFrames: Int = 0,
        val failedTrackingFrames: Int = 0,
        val poseJumpCount: Int = 0,
        val maxTranslationStepMeters: Float = 0f,
        val maxRotationStepDegrees: Float = 0f,
        val cameraTravelMeters: Float = 0f
    ) {
        val trackingRatio: Float
            get() = if (totalFrames <= 0) 0f else trackingFrames.toFloat() / totalFrames.toFloat()
    }

    private var totalFrames = 0
    private var trackingFrames = 0
    private var failedTrackingFrames = 0
    private var poseJumpCount = 0
    private var maxTranslationStepMeters = 0f
    private var maxRotationStepDegrees = 0f
    private var cameraTravelMeters = 0f

    private var previousTranslation: FloatArray? = null
    private var previousQuaternion: FloatArray? = null
    private var previousTimestampNs: Long = Long.MIN_VALUE

    @Synchronized
    fun reset() {
        totalFrames = 0
        trackingFrames = 0
        failedTrackingFrames = 0
        poseJumpCount = 0
        maxTranslationStepMeters = 0f
        maxRotationStepDegrees = 0f
        cameraTravelMeters = 0f
        previousTranslation = null
        previousQuaternion = null
        previousTimestampNs = Long.MIN_VALUE
    }

    @Synchronized
    fun observe(pose: Pose?, trackingState: TrackingState, frameTimestampNs: Long) {
        totalFrames++
        if (trackingState != TrackingState.TRACKING || pose == null) {
            failedTrackingFrames++
            previousTranslation = null
            previousQuaternion = null
            previousTimestampNs = Long.MIN_VALUE
            return
        }

        trackingFrames++
        val translation = FloatArray(3).also { pose.getTranslation(it, 0) }
        val quaternion = FloatArray(4).also { pose.getRotationQuaternion(it, 0) }

        val prevT = previousTranslation
        val prevQ = previousQuaternion
        val prevTs = previousTimestampNs
        if (prevT != null && prevQ != null && prevTs != Long.MIN_VALUE) {
            val dtSec = (frameTimestampNs - prevTs).toDouble() / 1_000_000_000.0
            if (dtSec > 0.0 && dtSec <= 0.25) {
                val dx = translation[0] - prevT[0]
                val dy = translation[1] - prevT[1]
                val dz = translation[2] - prevT[2]
                val step = sqrt(dx * dx + dy * dy + dz * dz)
                val rotation = quaternionDistanceDegrees(prevQ, quaternion)

                maxTranslationStepMeters = maxOf(maxTranslationStepMeters, step)
                maxRotationStepDegrees = maxOf(maxRotationStepDegrees, rotation)

                // Count only physically implausible short-interval jumps as a
                // tracking discontinuity. Normal slow scan motion is retained.
                if (step > 0.18f || rotation > 18f) {
                    poseJumpCount++
                } else {
                    cameraTravelMeters += step
                }
            }
        }

        previousTranslation = translation
        previousQuaternion = quaternion
        previousTimestampNs = frameTimestampNs
    }

    @Synchronized
    fun snapshot(): Snapshot = Snapshot(
        totalFrames = totalFrames,
        trackingFrames = trackingFrames,
        failedTrackingFrames = failedTrackingFrames,
        poseJumpCount = poseJumpCount,
        maxTranslationStepMeters = maxTranslationStepMeters,
        maxRotationStepDegrees = maxRotationStepDegrees,
        cameraTravelMeters = cameraTravelMeters
    )

    private fun quaternionDistanceDegrees(a: FloatArray, b: FloatArray): Float {
        if (a.size < 4 || b.size < 4) return 0f
        val dot = abs(
            a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]
        ).coerceIn(0f, 1f)
        return Math.toDegrees(2.0 * acos(dot.toDouble())).toFloat()
    }
}
