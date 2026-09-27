package jp.example.greenreader.analysis

import com.google.ar.core.Pose
import kotlin.math.sqrt

/**
 * Anchor-relative frame that keeps ARCore's world Y axis as vertical.
 *
 * Full Anchor.inverse() includes pitch/roll from the hit-test/plane pose. That can
 * rotate a flat floor into a steep local slope. This frame follows the anchor's
 * translation and yaw only, while explicitly discarding pitch/roll.
 */
data class GravityAlignedFrame(
    val originX: Float,
    val originY: Float,
    val originZ: Float,
    val rightX: Float,
    val rightZ: Float
) {
    private val forwardX: Float get() = -rightZ
    private val forwardZ: Float get() = rightX

    fun worldToLocal(world: FloatArray): FloatArray {
        val dx = world[0] - originX
        val dy = world[1] - originY
        val dz = world[2] - originZ
        return floatArrayOf(
            dx * rightX + dz * rightZ,
            dy,
            dx * forwardX + dz * forwardZ
        )
    }

    fun localToWorld(local: FloatArray): FloatArray {
        return floatArrayOf(
            originX + rightX * local[0] + forwardX * local[2],
            originY + local[1],
            originZ + rightZ * local[0] + forwardZ * local[2]
        )
    }

    companion object {
        fun fromPose(pose: Pose): GravityAlignedFrame {
            val t = pose.translation
            var axis = pose.rotateVector(floatArrayOf(1f, 0f, 0f))
            var nx = axis[0]
            var nz = axis[2]
            var len = sqrt(nx * nx + nz * nz)
            if (len < 1e-4f) {
                axis = pose.rotateVector(floatArrayOf(0f, 0f, -1f))
                nx = -axis[2]
                nz = axis[0]
                len = sqrt(nx * nx + nz * nz)
            }
            if (len < 1e-4f) {
                nx = 1f
                nz = 0f
                len = 1f
            }
            return GravityAlignedFrame(
                originX = t[0],
                originY = t[1],
                originZ = t[2],
                rightX = nx / len,
                rightZ = nz / len
            )
        }

        fun fromYawBasis(
            originX: Float,
            originY: Float,
            originZ: Float,
            rightX: Float,
            rightZ: Float
        ): GravityAlignedFrame {
            val len = sqrt(rightX * rightX + rightZ * rightZ).coerceAtLeast(1e-6f)
            return GravityAlignedFrame(originX, originY, originZ, rightX / len, rightZ / len)
        }
    }
}
