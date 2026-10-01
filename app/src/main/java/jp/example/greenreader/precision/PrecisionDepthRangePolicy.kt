package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Chooses the scan depth ceiling from the currently tracked marker geometry.
 * Keep the old 5 m floor for ordinary short scans, but never clip the cup end
 * simply because the cup is farther from the camera than the ball.
 */
object PrecisionDepthRangePolicy {
    fun maxDepthM(camera: Vec3, ball: Vec3, cup: Vec3?): Float {
        fun distance(p: Vec3): Float {
            val dx = p.x - camera.x
            val dy = p.y - camera.y
            val dz = p.z - camera.z
            return sqrt(dx * dx + dy * dy + dz * dz)
        }

        val farthest = max(distance(ball), cup?.let(::distance) ?: 0f)
        if (!farthest.isFinite()) return 5.0f
        return (farthest + 0.75f).coerceIn(5.0f, 12.0f)
    }
}
