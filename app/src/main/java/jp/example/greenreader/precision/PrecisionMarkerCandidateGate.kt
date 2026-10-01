package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Validate marker candidates before source selection.
 *
 * Ball marks keep the conservative 0.2..4 m camera-distance gate.
 * Cup marks may legitimately be farther from the camera than the ball, so
 * they are judged primarily relative to the already-fixed ball. The 12 m
 * ceiling matches the existing Full Depth tap sampling range and prevents
 * obviously remote/background geometry from being accepted.
 */
object PrecisionMarkerCandidateGate {
    data class Result(
        val reason: String?,
        val cameraDistance: Float,
        val horizontal: Float? = null,
        val vertical: Float? = null,
        val limit: Float? = null
    ) {
        val accepted: Boolean get() = reason == null
    }

    fun evaluate(camera: Vec3, candidate: Vec3, ball: Vec3? = null): Result {
        val dx = candidate.x - camera.x
        val dy = candidate.y - camera.y
        val dz = candidate.z - camera.z
        val d2 = dx * dx + dy * dy + dz * dz
        val distance = sqrt(d2)

        if (!d2.isFinite() || distance < 0.2f) {
            return Result("camera-distance", distance)
        }

        // The Ball is the reference origin for all later geometry. Keep it close
        // enough that the first anchor is based on reliable AR/Depth geometry.
        if (ball == null) {
            return if (distance <= 4.0f) {
                Result(null, distance)
            } else {
                Result("camera-distance", distance)
            }
        }

        val bx = candidate.x - ball.x
        val bz = candidate.z - ball.z
        val horizontal = sqrt(bx * bx + bz * bz)
        val vertical = abs(candidate.y - ball.y)
        val limit = max(0.08f, horizontal * 0.12f + 0.04f)

        val reason = when {
            !distance.isFinite() || !horizontal.isFinite() || !vertical.isFinite() ->
                "invalid-number"
            distance > 12.0f ->
                "camera-distance"
            vertical > limit ->
                "vertical-mismatch"
            else -> null
        }
        return Result(reason, distance, horizontal, vertical, limit)
    }
}
