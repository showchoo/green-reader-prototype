package jp.example.greenreader.precision

import kotlin.math.exp
import kotlin.math.sqrt

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
        radiusMeters: Float = 0.45f
    ): Fit? {
        val rows = ArrayList<Pair<DoubleArray, Pair<Double, Double>>>()
        val r2 = radiusMeters * radiusMeters

        for (c in cells) {
            val dx = c.x - centerX
            val dz = c.z - centerZ
            if (dx * dx + dz * dz > r2) continue

            val forward = dx * forwardX + dz * forwardZ
            val right = dx * rightX + dz * rightZ
            val dist = sqrt((forward * forward + right * right).toDouble())
            val spatial = exp(-0.5 * (dist / (radiusMeters * 0.55)).let { it * it })
            val stability = 1.0 / (1.0 + c.madMeters * 120.0)
            val obs = c.observations.coerceAtMost(12) / 12.0
            val w = spatial * c.confidence * stability * (0.5 + 0.5 * obs)

            rows += doubleArrayOf(
                forward.toDouble(),
                right.toDouble(),
                1.0
            ) to (c.height.toDouble() to w)
        }

        if (rows.size < 8) return null

        val ata = Array(3) { DoubleArray(3) }
        val aty = DoubleArray(3)
        for ((a, yw) in rows) {
            val y = yw.first
            val w = yw.second
            for (i in 0 until 3) {
                aty[i] += w * a[i] * y
                for (j in 0 until 3) ata[i][j] += w * a[i] * a[j]
            }
        }

        // Small ridge term keeps sparse/edge neighborhoods numerically stable.
        for (i in 0 until 3) ata[i][i] += 1e-6
        val beta = solve(ata, aty) ?: return null

        var se = 0.0
        var sw = 0.0
        for ((a, yw) in rows) {
            val y = yw.first
            val w = yw.second
            val pred = beta[0] * a[0] + beta[1] * a[1] + beta[2]
            val e = y - pred
            se += w * e * e
            sw += w
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
