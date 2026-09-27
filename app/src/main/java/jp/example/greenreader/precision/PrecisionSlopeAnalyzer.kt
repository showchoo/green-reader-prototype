package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.SlopeSegment
import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.sqrt

object PrecisionSlopeAnalyzer {
    private const val MAX_USABLE_SLOPE_PERCENT = 12f
    private const val MAX_LOCAL_RMSE_METERS = 0.040

    @Volatile var lastDiagnostic: String = ""
        private set

    fun analyze(
        surface: PrecisionSurfaceModel,
        ball: Vec3,
        cup: Vec3,
        segmentCount: Int = 8
    ): SlopeReport? {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val distance = sqrt(dx * dx + dz * dz)

        // Fail closed when the reconstructed ground is too sparse.
        if (distance < 0.4f || surface.groundCellCount < 25 || surface.uniqueFrames < 3) {
            lastDiagnostic = "precheck distance=" + String.format("%.2f", distance) +
                " ground=" + surface.groundCellCount +
                " frames=" + surface.uniqueFrames
            return null
        }

        val fx = dx / distance
        val fz = dz / distance
        val rx = -fz
        val rz = fx

        val segments = ArrayList<SlopeSegment>()
        var fitMissing = 0
        var rmseRejected = 0
        var slopeRejected = 0
        var maxSeenSlope = 0f
        var maxSeenRmse = 0.0
        for (i in 0 until segmentCount) {
            val t = (i + 0.5f) / segmentCount
            val cx = ball.x + dx * t
            val cz = ball.z + dz * t
            val fit = PrecisionLocalQuadraticFitter.fit(
                surface.cells, cx, cz, fx, fz, rx, rz
            )
            if (fit == null) {
                fitMissing++
                continue
            }

            if (fit.rmseMeters > maxSeenRmse) maxSeenRmse = fit.rmseMeters
            if (fit.rmseMeters > MAX_LOCAL_RMSE_METERS) {
                rmseRejected++
                continue
            }

            val forward = (fit.dHdForward * 100.0).toFloat()
            val right = (fit.dHdRight * 100.0).toFloat()
            val total = sqrt(forward * forward + right * right)
            if (total.isFinite() && total > maxSeenSlope) maxSeenSlope = total

            // A putting-green reading above this level is treated as a failed
            // reconstruction instead of being turned into an aim instruction.
            if (!forward.isFinite() || !right.isFinite() || total > MAX_USABLE_SLOPE_PERCENT) {
                slopeRejected++
                continue
            }

            val start = distance * i / segmentCount
            val end = distance * (i + 1) / segmentCount
            val elevation = ball.y + (cup.y - ball.y) * t
            segments += SlopeSegment(
                startMeters = start,
                endMeters = end,
                longitudinalPercent = forward,
                crossPercent = right,
                elevationMeters = elevation,
                sampleCount = fit.samples
            )
        }

        // Require broad coverage along the putt line, not one or two lucky patches.
        if (segments.size < 4) {
            lastDiagnostic =
                "segments=" + segments.size + "/" + segmentCount +
                " fitMissing=" + fitMissing +
                " rmseRejected=" + rmseRejected +
                " slopeRejected=" + slopeRejected +
                " maxRmse=" + String.format("%.3f", maxSeenRmse) +
                " maxSlope=" + String.format("%.1f", maxSeenSlope) + "%"
            return null
        }

        fun median(values: List<Float>): Float {
            val s = values.sorted()
            val m = s.size / 2
            return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) * 0.5f
        }

        val longitudinal = median(segments.map { it.longitudinalPercent })
        val cross = median(segments.map { it.crossPercent })
        if (abs(longitudinal) > MAX_USABLE_SLOPE_PERCENT ||
            abs(cross) > MAX_USABLE_SLOPE_PERCENT) {
            lastDiagnostic =
                "medianRejected long=" + String.format("%.2f", longitudinal) +
                " cross=" + String.format("%.2f", cross) +
                " segments=" + segments.size
            return null
        }

        lastDiagnostic =
            "OK segments=" + segments.size +
            " fitMissing=" + fitMissing +
            " rmseRejected=" + rmseRejected +
            " slopeRejected=" + slopeRejected +
            " maxRmse=" + String.format("%.3f", maxSeenRmse) +
            " maxSlope=" + String.format("%.1f", maxSeenSlope) + "%"

        return SlopeReport(
            distanceMeters = distance,
            segments = segments,
            overallLongitudinalPercent = longitudinal,
            overallCrossPercent = cross,
            pointCount = surface.sourcePointCount
        )
    }
}
