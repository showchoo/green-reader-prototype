package jp.example.greenreader.analysis

import kotlin.math.abs

/** Combines repeated short slope measurements into one stable result. */
object SlopeConsensus {
    private const val DEFAULT_MIN_AGREE = 3
    private const val FLAT_THRESHOLD_PERCENT = 0.15f

    fun combine(
        reports: List<SlopeReport>,
        minAgree: Int = DEFAULT_MIN_AGREE
    ): SlopeReport? {
        if (reports.size < minAgree) return null

        val overallCrossValues = reports.map { it.overallCrossPercent }
        val overallSign = majoritySign(overallCrossValues, minAgree) ?: return null
        val overallCross = consensusValue(overallCrossValues, overallSign)
        val overallLongitudinal = median(reports.map { it.overallLongitudinalPercent })
        val distance = median(reports.map { it.distanceMeters })

        val maxSegments = reports.maxOfOrNull { it.segments.size } ?: 0
        if (maxSegments == 0) return null

        val segments = ArrayList<SlopeSegment>(maxSegments)
        for (index in 0 until maxSegments) {
            val available = reports.mapNotNull { it.segments.getOrNull(index) }
            if (available.size < minAgree) continue

            val crossValues = available.map { it.crossPercent }
            val segmentSign = majoritySign(crossValues, minAgree) ?: overallSign
            segments += SlopeSegment(
                startMeters = median(available.map { it.startMeters }),
                endMeters = median(available.map { it.endMeters }),
                longitudinalPercent = median(available.map { it.longitudinalPercent }),
                crossPercent = consensusValue(crossValues, segmentSign),
                elevationMeters = median(available.map { it.elevationMeters }),
                sampleCount = medianInt(available.map { it.sampleCount })
            )
        }
        if (segments.isEmpty()) return null

        return SlopeReport(
            distanceMeters = distance,
            segments = segments,
            overallLongitudinalPercent = overallLongitudinal,
            overallCrossPercent = overallCross,
            pointCount = medianInt(reports.map { it.pointCount })
        )
    }

    private fun vote(value: Float): Int = when {
        value > FLAT_THRESHOLD_PERCENT -> 1
        value < -FLAT_THRESHOLD_PERCENT -> -1
        else -> 0
    }

    private fun majoritySign(values: List<Float>, minAgree: Int): Int? {
        val positive = values.count { vote(it) > 0 }
        val negative = values.count { vote(it) < 0 }
        val flat = values.count { vote(it) == 0 }
        return when {
            positive >= minAgree && positive > negative && positive > flat -> 1
            negative >= minAgree && negative > positive && negative > flat -> -1
            flat >= minAgree && flat > positive && flat > negative -> 0
            else -> null
        }
    }

    private fun consensusValue(values: List<Float>, sign: Int): Float {
        if (sign == 0) return 0f
        val matching = values.filter { vote(it) == sign }
        val source = if (matching.isNotEmpty()) matching else values
        return median(source)
    }

    private fun median(values: List<Float>): Float {
        if (values.isEmpty()) return 0f
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 == 1) {
            sorted[middle]
        } else {
            (sorted[middle - 1] + sorted[middle]) * 0.5f
        }
    }

    private fun medianInt(values: List<Int>): Int {
        if (values.isEmpty()) return 0
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 == 1) {
            sorted[middle]
        } else {
            (sorted[middle - 1] + sorted[middle]) / 2
        }
    }
}
