package jp.example.greenreader.precision

import kotlin.math.exp
import kotlin.math.sqrt

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
            val s = dx * forwardX + dz * forwardZ
            val t = dx * rightX + dz * rightZ
            val dist = sqrt((s * s + t * t).toDouble())
            val spatial = exp(-0.5 * (dist / (radiusMeters * 0.55)).let { it * it })
            val stability = 1.0 / (1.0 + c.madMeters * 120.0)
            val obs = c.observations.coerceAtMost(12) / 12.0
            val w = spatial * c.confidence * stability * (0.5 + 0.5 * obs)
            val a = doubleArrayOf(
                (s * s).toDouble(), (t * t).toDouble(), (s * t).toDouble(),
                s.toDouble(), t.toDouble(), 1.0
            )
            rows += a to (c.height.toDouble() to w)
        }
        if (rows.size < 12) return null

        val ata = Array(6) { DoubleArray(6) }
        val aty = DoubleArray(6)
        for ((a, yw) in rows) {
            val y = yw.first
            val w = yw.second
            for (i in 0 until 6) {
                aty[i] += w * a[i] * y
                for (j in 0 until 6) ata[i][j] += w * a[i] * a[j]
            }
        }
        for (i in 0 until 6) ata[i][i] += 1e-8
        val beta = solve(ata, aty) ?: return null

        var se = 0.0
        var sw = 0.0
        for ((a, yw) in rows) {
            val y = yw.first
            val w = yw.second
            var pred = 0.0
            for (i in 0 until 6) pred += beta[i] * a[i]
            val e = y - pred
            se += w * e * e
            sw += w
        }
        return Fit(beta[3], beta[4], sqrt(se / sw.coerceAtLeast(1e-9)), rows.size)
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
                val f = a[r][col]
                for (j in col until n) a[r][j] -= f * a[col][j]
                b[r] -= f * b[col]
            }
        }
        return b
    }
}
