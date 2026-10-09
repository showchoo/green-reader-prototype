package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.hypot

/**
 * Establish the reference *locally* rather than from the most populated
 * height bin in the whole visible scene. Repeated points on furniture,
 * walls, or the interpolated background must never outvote sparse nearby
 * physical ground.
 *
 * Ball/cup anchor height is a coarse sanity envelope (20 cm), NOT ground
 * truth or an absolute calibration. A weak or ambiguous reference is rejected.
 */
object PrecisionAnchoredGroundSelector {
    data class Observation(
        val x: Float,
        val z: Float,
        val height: Float
    )

    enum class Status { ANCHORED, NO_NEAR_BALL_GROUND, AMBIGUOUS_HEIGHT }

    data class Decision(
        val status: Status,
        val referenceHeight: Float?,
        val nearbyCount: Int,
        val matchedHeightCount: Int,
        val radiusMeters: Float,
        val seedIndices: List<Int>
    ) {
        val valid: Boolean get() = status == Status.ANCHORED &&
            referenceHeight != null && seedIndices.size >= 8

        fun diagnostic(): String =
            "ANCHORED_GROUND status=" + status +
            " ref=" + (referenceHeight?.let {
                String.format(java.util.Locale.US, "%.3f", it)
            } ?: "-") +
            " near=" + nearbyCount +
            " matched=" + matchedHeightCount +
            " radius=" + String.format(java.util.Locale.US, "%.2f", radiusMeters) +
            " seeds=" + seedIndices.size
    }

    fun select(stable: List<Observation>, ball: Vec3): Decision {
        if (!ball.x.isFinite() || !ball.y.isFinite() || !ball.z.isFinite())
            return Decision(Status.NO_NEAR_BALL_GROUND, null, 0, 0, 0f, emptyList())

        fun near(index: Int, radius: Float): Boolean {
            val p = stable[index]
            return p.x.isFinite() && p.z.isFinite() && p.height.isFinite() &&
                hypot((p.x - ball.x).toDouble(), (p.z - ball.z).toDouble()) <= radius &&
                abs(p.height - ball.y) <= .20f
        }

        val near35 = stable.indices.filter { near(it, .35f) }
        val radius: Float
        val eligible: List<Int>
        if (near35.size >= 12) {
            radius = .35f
            eligible = near35
        } else {
            val near55 = stable.indices.filter { near(it, .55f) }
            if (near55.size < 18) {
                return Decision(Status.NO_NEAR_BALL_GROUND, null, near55.size,
                    0, .55f, emptyList())
            }
            radius = .55f
            eligible = near55
        }

        // Prefer the best-supported local height mode. A 5 cm bin alone is
        // too coarse for putting; it only identifies a candidate local layer.
        val bins = eligible.groupBy {
            floor(stable[it].height / .05f).toInt()
        }
        val selectedBin = bins.entries.sortedWith(
            compareByDescending<Map.Entry<Int, List<Int>>> { it.value.size }
                .thenBy { abs((it.key + .5f) * .05f - ball.y) }
                .thenBy { it.key }
        ).firstOrNull()?.key
            ?: return Decision(Status.AMBIGUOUS_HEIGHT, null, eligible.size,
                0, radius, emptyList())

        val center = (selectedBin + .5f) * .05f
        val supported = eligible.filter { abs(stable[it].height - center) <= .075f }
        if (supported.size < 10) {
            return Decision(Status.AMBIGUOUS_HEIGHT, null, eligible.size,
                supported.size, radius, emptyList())
        }
        val heights = supported.map { stable[it].height }.sorted()
        val mid = heights.size / 2
        val reference = if (heights.size % 2 == 1) heights[mid]
            else (heights[mid - 1] + heights[mid]) * .5f

        // The seed must be spatially close to the actual ball anchor, not
        // merely near the global origin or the center of the scene.
        val seedIndices = stable.indices.asSequence()
            .filter {
                near(it, .55f) && abs(stable[it].height - reference) <= .085f
            }
            .sortedWith(
                compareBy<Int> {
                    hypot(
                        (stable[it].x - ball.x).toDouble(),
                        (stable[it].z - ball.z).toDouble()
                    )
                }.thenBy { abs(stable[it].height - reference) }
            )
            .take(16).toList()

        return if (seedIndices.size < 8) {
            Decision(Status.AMBIGUOUS_HEIGHT, reference, eligible.size,
                supported.size, radius, seedIndices)
        } else {
            Decision(Status.ANCHORED, reference, eligible.size,
                supported.size, radius, seedIndices)
        }
    }
}
