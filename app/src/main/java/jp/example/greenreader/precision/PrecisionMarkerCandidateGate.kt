package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/** Apply the existing marker bounds before choosing a source, not only after it. */
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
        if (!d2.isFinite() || d2 !in 0.04f..16f) {
            return Result("camera-distance", distance)
        }
        if (ball == null) return Result(null, distance)
        val bx = candidate.x - ball.x
        val bz = candidate.z - ball.z
        val horizontal = sqrt(bx * bx + bz * bz)
        val vertical = abs(candidate.y - ball.y)
        val limit = max(0.08f, horizontal * 0.12f + 0.04f)
        val reason = when {
            !horizontal.isFinite() || !vertical.isFinite() -> "invalid-number"
            vertical > limit -> "vertical-mismatch"
            else -> null
        }
        return Result(reason, distance, horizontal, vertical, limit)
    }
}
