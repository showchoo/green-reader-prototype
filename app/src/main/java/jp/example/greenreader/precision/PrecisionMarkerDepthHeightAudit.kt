package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Independent marker-vs-Depth height-change consistency *diagnostic*.
 * Never assumes the ground is level and never modifies the reported slope.
 *
 * The reference uses the median of accepted ground surface cells near each
 * marker. It is not independent physical ground truth: both signals use
 * ARCore and can share the same failure mode.
 */
object PrecisionMarkerDepthHeightAudit {
    enum class Status { INSUFFICIENT_COVERAGE, CONSISTENT, DISAGREEMENT }

    data class Result(
        val status: Status,
        val markerDeltaMeters: Float,
        val depthDeltaMeters: Float?,
        val discrepancyMeters: Float?,
        val nearBallCells: Int,
        val nearCupCells: Int,
        val independentGroundTruth: Boolean = false
    ) {
        val trustForQuality: Boolean
            get() = status != Status.DISAGREEMENT

        fun summary(): String = buildString {
            append("MARKER_DEPTH_HEIGHT status=").append(status)
            append(" markerDeltaM=").append(format(markerDeltaMeters))
            append(" depthDeltaM=").append(format(depthDeltaMeters))
            append(" discrepancyM=").append(format(discrepancyMeters))
            append(" ballCells=").append(nearBallCells)
            append(" cupCells=").append(nearCupCells)
            append(" independentGroundTruth=false")
        }

        private fun format(v: Float?): String = if (v == null || !v.isFinite()) "-" else
            String.format(java.util.Locale.US, "%.5f", v)
    }

    fun evaluate(
        surface: PrecisionSurfaceModel?,
        ball: Vec3,
        cup: Vec3
    ): Result {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val distance = hypot(dx.toDouble(), dz.toDouble()).toFloat()
        val markerDelta = cup.y - ball.y
        if (!distance.isFinite() || distance < .4f || !markerDelta.isFinite() ||
            surface == null || surface.groundCellCount < 25
        ) return Result(Status.INSUFFICIENT_COVERAGE, markerDelta, null, null, 0, 0)
        val fx = dx / distance
        val fz = dz / distance
        val nearRadius = max(.12f, minOf(.16f, distance * .24f))
        val ballHeights = ArrayList<Float>()
        val cupHeights = ArrayList<Float>()
        for (cell in surface.cells) {
            if (!cell.height.isFinite() || !cell.x.isFinite() || !cell.z.isFinite()) continue
            val rx = cell.x - ball.x
            val rz = cell.z - ball.z
            val along = rx * fx + rz * fz
            val lateral = abs(-rx * fz + rz * fx)
            if (lateral > .18f) continue
            if (along in -nearRadius..nearRadius) ballHeights.add(cell.height)
            if (along in (distance-nearRadius)..(distance+nearRadius))
                cupHeights.add(cell.height)
        }
        if (ballHeights.size < 6 || cupHeights.size < 6)
            return Result(Status.INSUFFICIENT_COVERAGE, markerDelta, null, null,
                ballHeights.size, cupHeights.size)
        val depthDelta = median(cupHeights) - median(ballHeights)
        val discrepancy = abs(depthDelta-markerDelta)
        if (!discrepancy.isFinite())
            return Result(Status.INSUFFICIENT_COVERAGE, markerDelta, null, null,
                ballHeights.size, cupHeights.size)
        // Observational flag: a 4cm discrepancy cannot be explained by
        // surface median quantization alone; NOT a claim of cm-accuracy.
        val state = if (discrepancy >= .04f) Status.DISAGREEMENT else Status.CONSISTENT
        return Result(state, markerDelta, depthDelta, discrepancy,
            ballHeights.size, cupHeights.size)
    }

    private fun median(data: List<Float>): Float {
        val sorted = data.sorted()
        val center = sorted.size / 2
        return if (sorted.size % 2 == 1) sorted[center] else
            (sorted[center-1] + sorted[center]) / 2f
    }
}
