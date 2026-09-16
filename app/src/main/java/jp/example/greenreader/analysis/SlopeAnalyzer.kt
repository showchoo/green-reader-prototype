package jp.example.greenreader.analysis

import kotlin.math.abs
import kotlin.math.sqrt

object SlopeAnalyzer {
    private data class Sample(val s: Float, val t: Float, val h: Float)
    private data class PlaneFit(
        val longitudinal: Float,
        val cross: Float,
        val intercept: Float,
        val sampleCount: Int,
        val lateralSpan: Float,
        val residualMad: Float
    )

    fun analyze(
        points: List<Vec3>,
        ball: Vec3,
        cup: Vec3,
        corridorHalfWidthM: Float = 0.65f,
        bins: Int = 8
    ): SlopeReport? {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val dist = sqrt(dx * dx + dz * dz)
        if (dist < 0.4f) return null
        val ux = dx / dist
        val uz = dz / dist
        val vx = -uz
        val vz = ux

        val corridor = points.mapNotNull { p ->
            val rx = p.x - ball.x
            val rz = p.z - ball.z
            val s = rx * ux + rz * uz
            val t = rx * vx + rz * vz
            if (s in -0.25f..(dist + 0.25f) && abs(t) <= corridorHalfWidthM) Sample(s, t, p.y) else null
        }
        if (corridor.size < 80) return null

        // The complete corridor is much less sensitive to sparse/noisy depth near the cup.
        val allFit = robustFitPlane(corridor) ?: return null
        val segments = (0 until bins).mapNotNull { i ->
            val a = dist * i / bins
            val b = dist * (i + 1) / bins
            val local = corridor.filter { it.s in a..b }
            if (local.size < 8) null else {
                val localFit = robustFitPlane(local) ?: return@mapNotNull null
                val cross = stabilizeLocalCrossSlope(localFit, allFit.cross, corridorHalfWidthM * 2f)
                val mid = (a + b) * 0.5f
                val elev = localFit.longitudinal * mid + localFit.intercept
                SlopeSegment(a, b, localFit.longitudinal * 100f, cross * 100f, elev, localFit.sampleCount)
            }
        }
        if (segments.isEmpty()) return null

        return SlopeReport(
            dist,
            segments,
            allFit.longitudinal * 100f,
            allFit.cross * 100f,
            allFit.sampleCount
        )
    }

    /**
     * Preserve a genuine change of break, but require broad, clean local data before
     * showing a direction opposite to the well-supported full-corridor slope.
     */
    private fun stabilizeLocalCrossSlope(local: PlaneFit, overallCross: Float, corridorWidth: Float): Float {
        val coverage = (local.lateralSpan / corridorWidth.coerceAtLeast(0.01f)).coerceIn(0f, 1f)
        val sampleStrength = (local.sampleCount / 80f).coerceIn(0f, 1f)
        val noiseStrength = (1f / (1f + local.residualMad / 0.012f)).coerceIn(0f, 1f)
        val reliability = (coverage * sampleStrength * noiseStrength).coerceIn(0.10f, 0.85f)
        val blended = overallCross + reliability * (local.cross - overallCross)

        val oppositeDirection = overallCross * blended < 0f
        val meaningfulOverall = abs(overallCross) >= 0.003f // 0.3%
        val strongLocalReversal = reliability >= 0.65f && abs(local.cross) >= abs(overallCross) * 1.5f
        return if (oppositeDirection && meaningfulOverall && !strongLocalReversal) {
            overallCross * 0.25f
        } else {
            blended
        }
    }

    /** Iteratively remove depth outliers using the median absolute residual. */
    private fun robustFitPlane(data: List<Sample>): PlaneFit? {
        var kept = data
        repeat(3) {
            val coefficients = leastSquares(kept) ?: return null
            val residuals = kept.map {
                abs(it.h - (coefficients.first * it.s + coefficients.second * it.t + coefficients.third))
            }
            val gate = maxOf(0.012f, median(residuals) * 3.5f)
            val filtered = kept.filterIndexed { index, _ -> residuals[index] <= gate }
            if (filtered.size >= 8 && filtered.size < kept.size) kept = filtered
        }

        val coefficients = leastSquares(kept) ?: return null
        val residualMad = median(kept.map {
            abs(it.h - (coefficients.first * it.s + coefficients.second * it.t + coefficients.third))
        })
        val lateralSpan = percentile(kept.map { it.t }, 0.90f) - percentile(kept.map { it.t }, 0.10f)
        return PlaneFit(
            coefficients.first,
            coefficients.second,
            coefficients.third,
            kept.size,
            lateralSpan.coerceAtLeast(0f),
            residualMad
        )
    }

    private fun leastSquares(data: List<Sample>): Triple<Float, Float, Float>? {
        var ss = 0.0; var tt = 0.0; var st = 0.0
        var s = 0.0; var t = 0.0; var h = 0.0
        var sh = 0.0; var th = 0.0
        val n = data.size.toDouble()
        for (p in data) {
            val sd = p.s.toDouble(); val td = p.t.toDouble(); val hd = p.h.toDouble()
            ss += sd * sd; tt += td * td; st += sd * td
            s += sd; t += td; h += hd; sh += sd * hd; th += td * hd
        }
        val matrix = arrayOf(
            doubleArrayOf(ss, st, s, sh),
            doubleArrayOf(st, tt, t, th),
            doubleArrayOf(s, t, n, h)
        )
        for (col in 0..2) {
            var pivot = col
            for (row in col + 1..2) if (abs(matrix[row][col]) > abs(matrix[pivot][col])) pivot = row
            if (abs(matrix[pivot][col]) < 1e-9) return null
            val tmp = matrix[col]; matrix[col] = matrix[pivot]; matrix[pivot] = tmp
            val divisor = matrix[col][col]
            for (column in col..3) matrix[col][column] /= divisor
            for (row in 0..2) if (row != col) {
                val factor = matrix[row][col]
                for (column in col..3) matrix[row][column] -= factor * matrix[col][column]
            }
        }
        return Triple(matrix[0][3].toFloat(), matrix[1][3].toFloat(), matrix[2][3].toFloat())
    }

    private fun median(values: List<Float>): Float = percentile(values, 0.5f)

    private fun percentile(values: List<Float>, fraction: Float): Float {
        if (values.isEmpty()) return 0f
        val sorted = values.sorted()
        val index = (sorted.lastIndex * fraction.coerceIn(0f, 1f)).toInt()
        return sorted[index]
    }
}
