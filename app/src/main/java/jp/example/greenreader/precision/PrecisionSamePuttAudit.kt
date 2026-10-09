package jp.example.greenreader.precision

import kotlin.math.abs
import kotlin.math.max

/**
 * Field-test audit across completed scans of the SAME anchored putt.
 * This does not establish absolute accuracy or correct the measured grade.
 */
object PrecisionSamePuttAudit {
    enum class Status { FIRST_SCAN, CONSISTENT, CONFLICT, NO_REPORT }
    data class Result(
        val status: Status,
        val comparisons: Int,
        val maxLongDifferencePp: Float,
        val maxCrossDifferencePp: Float,
        val signFlip: Boolean
    ) {
        val blocksDirection get() = status == Status.CONFLICT
        fun summary(): String =
            "SAME_PUTT status=" + status +
            " comparisons=" + comparisons +
            " maxLongDeltaPp=" + format(maxLongDifferencePp) +
            " maxCrossDeltaPp=" + format(maxCrossDifferencePp) +
            " signFlip=" + signFlip
        private fun format(value: Float): String =
            if (!value.isFinite()) "NA"
            else String.format(java.util.Locale.US, "%.2f", value)
    }

    // Pair(first=longitudinal, second=cross). Historical results refer to the
    // same two physical markers, not a new putt or a new camera session.
    fun evaluate(
        previous: List<Pair<Float, Float>>,
        current: Pair<Float, Float>?
    ): Result {
        if (current == null || !current.first.isFinite() ||
            !current.second.isFinite())
            return Result(Status.NO_REPORT, 0, Float.NaN, Float.NaN, false)
        val good = previous.filter { it.first.isFinite() && it.second.isFinite() }
        if (good.isEmpty())
            return Result(Status.FIRST_SCAN, 0, Float.NaN, Float.NaN, false)
        val maxLong = good.maxOf { abs(it.first - current.first) }
        val maxCross = good.maxOf { abs(it.second - current.second) }
        val flip = good.any {
            (abs(it.first) >= 2.0f && abs(current.first) >= 2.0f &&
                it.first * current.first < 0f) ||
            (abs(it.second) >= 2.0f && abs(current.second) >= 2.0f &&
                it.second * current.second < 0f)
        }
        // 4 percentage points is far larger than acceptable repeatability
        // for the exact same markers, not a declared cm-level accuracy bound.
        val conflict = flip || max(maxLong, maxCross) >= 4.0f
        return Result(if (conflict) Status.CONFLICT else Status.CONSISTENT,
            good.size, maxLong, maxCross, flip)
    }
}
