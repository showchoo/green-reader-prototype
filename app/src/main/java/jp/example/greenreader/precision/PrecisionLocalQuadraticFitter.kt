package jp.example.greenreader.precision

import kotlin.math.exp
import kotlin.math.sqrt
import kotlin.math.abs

/**
 * Robust local plane fit for putting-green slope.
 *
 * The previous 6-parameter quadratic fit could produce very large edge
 * derivatives from modest depth curvature/noise while still reporting a low
 * RMSE. For local slope we only need the first derivatives, so fit
 * h = a*s + b*t + c directly with the same spatial/stability weighting.
 */
object PrecisionLocalQuadraticFitter {
    data class Fit(
        val dHdForward: Double,
        val dHdRight: Double,
        val rmseMeters: Double,
        val samples: Int
    )

    fun fit(
        cells: List<PrecisionSurfaceCell>,
        centerX: Float,
        centerZ: Float,
        forwardX: Float,
        forwardZ: Float,
        rightX: Float,
        rightZ: Float,
        radiusMeters: Float = 0.32f
    ): Fit? {
        data class Row(
            val forward: Double,
            val right: Double,
            val height: Double,
            val baseWeight: Double
        )

        val rows = ArrayList<Row>()
        val r2 = radiusMeters * radiusMeters
        var minForward = Double.POSITIVE_INFINITY
        var maxForward = Double.NEGATIVE_INFINITY
        var minRight = Double.POSITIVE_INFINITY
        var maxRight = Double.NEGATIVE_INFINITY

        for (c in cells) {
            val dx = c.x - centerX
            val dz = c.z - centerZ
            if (dx * dx + dz * dz > r2) continue

            val forward = (dx * forwardX + dz * forwardZ).toDouble()
            val right = (dx * rightX + dz * rightZ).toDouble()
            val dist = sqrt(forward * forward + right * right)
            val spatial = exp(-0.5 * (dist / (radiusMeters * 0.58)).let { it * it })
            val stability = 1.0 / (1.0 + c.madMeters * 120.0)
            val obs = c.observations.coerceAtMost(12) / 12.0
            val w = spatial * c.confidence * stability * (0.5 + 0.5 * obs)

            rows += Row(forward, right, c.height.toDouble(), w)
            if (forward < minForward) minForward = forward
            if (forward > maxForward) maxForward = forward
            if (right < minRight) minRight = right
            if (right > maxRight) maxRight = right
        }

        if (rows.size < 10) return null

        // A slope is only observable when the neighborhood actually spans both
        // sides of the requested derivative. Reject one-sided edge fits instead
        // of extrapolating a steep plane from them.
        val minSideSupport = 0.10
        if (minForward > -minSideSupport || maxForward < minSideSupport ||
            minRight > -minSideSupport || maxRight < minSideSupport) {
            return null
        }

        fun solveWeighted(extraWeights: DoubleArray?): DoubleArray? {
            val ata = Array(3) { DoubleArray(3) }
            val aty = DoubleArray(3)
            for (i in rows.indices) {
                val r = rows[i]
                val w = r.baseWeight * (extraWeights?.get(i) ?: 1.0)
                val a0 = r.forward
                val a1 = r.right
                val a2 = 1.0
                val a = doubleArrayOf(a0, a1, a2)
                for (j in 0 until 3) {
                    aty[j] += w * a[j] * r.height
                    for (k in 0 until 3) ata[j][k] += w * a[j] * a[k]
                }
            }
            for (i in 0 until 3) ata[i][i] += 1e-6
            return solve(ata, aty)
        }

        var beta = solveWeighted(null) ?: return null

        // Two robust IRLS passes. Full Depth occasionally contributes coherent
        // but wrong edge cells; Huber weights stop them from steering the plane.
        repeat(2) {
            val residuals = rows.map { r ->
                r.height - (beta[0] * r.forward + beta[1] * r.right + beta[2])
            }
            val absResiduals = residuals.map { abs(it) }.sorted()
            val medianAbs = absResiduals[absResiduals.size / 2]
            val scale = (1.4826 * medianAbs).coerceAtLeast(0.008)
            val huberK = 1.5 * scale
            val robust = DoubleArray(rows.size) { i ->
                val a = abs(residuals[i])
                if (a <= huberK) 1.0 else huberK / a
            }
            beta = solveWeighted(robust) ?: return null
        }

        var se = 0.0
        var sw = 0.0
        for (r in rows) {
            val pred = beta[0] * r.forward + beta[1] * r.right + beta[2]
            val e = r.height - pred
            se += r.baseWeight * e * e
            sw += r.baseWeight
        }

        return Fit(
            dHdForward = beta[0],
            dHdRight = beta[1],
            rmseMeters = sqrt(se / sw.coerceAtLeast(1e-9)),
            samples = rows.size
        )
    }

    private fun solve(aIn: Array<DoubleArray>, bIn: DoubleArray): DoubleArray? {
        val n = bIn.size
        val a = Array(n) { aIn[it].clone() }
        val b = bIn.clone()
        for (col in 0 until n) {
            var pivot = col
            for (r in col + 1 until n) {
                if (kotlin.math.abs(a[r][col]) > kotlin.math.abs(a[pivot][col])) pivot = r
            }
            if (kotlin.math.abs(a[pivot][col]) < 1e-12) return null
            if (pivot != col) {
                val tmp = a[col]; a[col] = a[pivot]; a[pivot] = tmp
                val tb = b[col]; b[col] = b[pivot]; b[pivot] = tb
            }
            val div = a[col][col]
            for (j in col until n) a[col][j] /= div
            b[col] /= div
            for (r in 0 until n) {
                if (r == col) continue
                val factor = a[r][col]
                for (j in col until n) a[r][j] -= factor * a[col][j]
                b[r] -= factor * b[col]
            }
        }
        return b
    }
}
