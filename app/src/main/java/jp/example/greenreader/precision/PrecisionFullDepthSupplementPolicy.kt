package jp.example.greenreader.precision

import kotlin.math.max

/** Decides when Full Depth must supplement sparse Raw Depth on long scans. */
object PrecisionFullDepthSupplementPolicy {
    data class Plan(val useFull: Boolean, val minDepthM: Float)

    fun plan(
        rawAccepted: Boolean,
        requestedMinDepthM: Float,
        requestedMaxDepthM: Float,
        ballAxialDepthM: Float
    ): Plan {
        if (!rawAccepted) return Plan(true, requestedMinDepthM)

        // Preserve the proven Raw-first behavior for ordinary short scans.
        if (requestedMaxDepthM <= 5.0f) return Plan(false, requestedMinDepthM)

        // Long scans need dense coverage from around the Ball through the Cup.
        // Start slightly before the Ball along the camera Z axis so there is an
        // overlap zone for continuity, while avoiding Full Depth dominating the
        // entire near field.
        val start = if (ballAxialDepthM.isFinite() && ballAxialDepthM > 0f) {
            max(requestedMinDepthM, ballAxialDepthM - 0.50f)
        } else {
            requestedMinDepthM
        }
        return Plan(true, start.coerceAtMost(requestedMaxDepthM))
    }
}
