package jp.example.greenreader.analysis

import kotlin.math.abs

/**
 * Combines repeated short slope measurements into one stable result.
 *
 * v1.3 deliberately treats very small cross slopes conservatively. ARCore depth
 * can carry a repeatable sub-percent tilt bias even on a physically flat floor;
 * a 4/5 majority alone cannot reject a systematic bias.
 */
object SlopeConsensus {
    private const val DEFAULT_MIN_AGREE = 3
    private const val FLAT_THRESHOLD_PERCENT = 0.60f
    private const val WEAK_SLOPE_LIMIT_PERCENT = 1.00f

    fun combine(
        reports: List<SlopeReport>,
        minAgree: Int = DEFAULT_MIN_AGREE
    ): SlopeReport? {
        if (reports.size < minAgree) return null

        val overallCrossValues = reports.map { it.overallCrossPercent }
        val overallCross = conservativeCrossConsensus(overallCrossValues, minAgree) ?: return null
        val overallSign = vote(overallCross)
        val overallLongitudinal = median(reports.map { it.overallLongitudinalPercent })
        val distance = median(reports.map { it.distanceMeters })

        val maxSegments = reports.maxOfOrNull { it.segments.size } ?: 0
        if (maxSegments == 0) return null

        val segments = ArrayList<SlopeSegment>(maxSegments)
        for (index in 0 until maxSegments) {
            val available = reports.mapNotNull { it.segments.getOrNull(index) }
            if (available.size < minAgree) continue

            val crossValues = available.map { it.crossPercent }
            val cross = conservativeCrossConsensus(crossValues, minAgree)
                ?: if (overallSign == 0) 0f else overallCross

            segments += SlopeSegment(
                startMeters = median(available.map { it.startMeters }),
                endMeters = median(available.map { it.endMeters }),
                longitudinalPercent = median(available.map { it.longitudinalPercent }),
                crossPercent = cross,
                elevationMeters = median(available.map { it.elevationMeters }),
                sampleCount = medianInt(available.map { it.sampleCount })
            )
        }
        if (segments.isEmpty()) return null

        // If the overall result is flat, do not let noisy local bins resurrect a
        // directional break. This is the key flat-floor false-positive guard.
        val guardedSegments = if (overallSign == 0) {
            segments.map { it.copy(crossPercent = 0f) }
        } else {
            segments
        }

        return SlopeReport(
            distanceMeters = distance,
            segments = guardedSegments,
            overallLongitudinalPercent = overallLongitudinal,
            overallCrossPercent = overallCross,
            pointCount = medianInt(reports.map { it.pointCount })
        )
    }

    private fun conservativeCrossConsensus(values: List<Float>, minAgree: Int): Float? {
        if (values.size < minAgree) return null

        // Median absolute magnitude below 0.6% is treated as flat regardless of
        // sign agreement. This suppresses repeatable ARCore zero-offset bias.
        val medianValue = median(values)
        val medianAbs = median(values.map { abs(it) })
        if (medianAbs < FLAT_THRESHOLD_PERCENT) return 0f

        val positive = values.count { it >= FLAT_THRESHOLD_PERCENT }
        val negative = values.count { it <= -FLAT_THRESHOLD_PERCENT }
        val flat = values.size - positive - negative

        // Weak 0.6-1.0% slopes require unanimous direction across all windows.
        if (medianAbs < WEAK_SLOPE_LIMIT_PERCENT) {
            return when {
                positive == values.size -> median(values.filter { it > 0f })
                negative == values.size -> median(values.filter { it < 0f })
                flat >= minAgree -> 0f
                else -> 0f
            }
        }

        // Clearer slopes retain the proven majority-vote behavior.
        return when {
            positive >= minAgree && positive > negative && positive > flat ->
                median(values.filter { it >= FLAT_THRESHOLD_PERCENT })
            negative >= minAgree && negative > positive && negative > flat ->
                median(values.filter { it <= -FLAT_THRESHOLD_PERCENT })
            flat >= minAgree && flat >= positive && flat >= negative -> 0f
            else -> null
        }
    }

    private fun vote(value: Float): Int = when {
        value > FLAT_THRESHOLD_PERCENT -> 1
        value < -FLAT_THRESHOLD_PERCENT -> -1
        else -> 0
    }

    private fun median(values: List<Float>): Float {
        if (values.isEmpty()) return 0f
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 == 1) sorted[middle]
        else (sorted[middle - 1] + sorted[middle]) * 0.5f
    }

    private fun medianInt(values: List<Int>): Int {
        if (values.isEmpty()) return 0
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 == 1) sorted[middle]
        else (sorted[middle - 1] + sorted[middle]) / 2
    }
}
