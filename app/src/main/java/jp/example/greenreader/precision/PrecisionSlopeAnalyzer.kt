package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.SlopeSegment
import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.sqrt

object PrecisionSlopeAnalyzer {
    private const val MAX_USABLE_SLOPE_PERCENT = 12f
    private const val MAX_LOCAL_RMSE_METERS = 0.040
    private const val LOCAL_FIT_RADIUS_METERS = 0.45f

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
        val segmentDiagnostics = ArrayList<String>(segmentCount)
        var fitMissing = 0
        var rmseRejected = 0
        var slopeRejected = 0
        var maxSeenSlope = 0f
        var maxSeenRmse = 0.0

        fun nearbySamples(cx: Float, cz: Float): Int {
            val r2 = LOCAL_FIT_RADIUS_METERS * LOCAL_FIT_RADIUS_METERS
            return surface.cells.count { c ->
                val sx = c.x - cx
                val sz = c.z - cz
                sx * sx + sz * sz <= r2
            }
        }

        for (i in 0 until segmentCount) {
            val t = (i + 0.5f) / segmentCount
            val cx = ball.x + dx * t
            val cz = ball.z + dz * t
            val nearby = nearbySamples(cx, cz)
            val fit = PrecisionLocalQuadraticFitter.fit(
                surface.cells, cx, cz, fx, fz, rx, rz,
                radiusMeters = LOCAL_FIT_RADIUS_METERS
            )
            if (fit == null) {
                fitMissing++
                segmentDiagnostics += "S${i + 1} fit=null n=$nearby"
                continue
            }

            if (fit.rmseMeters > maxSeenRmse) maxSeenRmse = fit.rmseMeters
            val forward = (fit.dHdForward * 100.0).toFloat()
            val right = (fit.dHdRight * 100.0).toFloat()
            val total = sqrt(forward * forward + right * right)
            if (total.isFinite() && total > maxSeenSlope) maxSeenSlope = total

            val values =
                "n=${fit.samples} rmse=" + String.format("%.3f", fit.rmseMeters) +
                " f=" + String.format("%.1f", forward) + "%" +
                " r=" + String.format("%.1f", right) + "%" +
                " total=" + String.format("%.1f", total) + "%"

            if (fit.rmseMeters > MAX_LOCAL_RMSE_METERS) {
                rmseRejected++
                segmentDiagnostics += "S${i + 1} RMSE>4cm $values"
                continue
            }

            if (!forward.isFinite() || !right.isFinite() || !total.isFinite()) {
                slopeRejected++
                segmentDiagnostics += "S${i + 1} nonfinite $values"
                continue
            }
            if (total > MAX_USABLE_SLOPE_PERCENT) {
                slopeRejected++
                segmentDiagnostics += "S${i + 1} slope>12% $values"
                continue
            }

            segmentDiagnostics += "S${i + 1} OK $values"
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

        val prefix =
            "distance=" + String.format("%.2f", distance) +
            " ground=" + surface.groundCellCount +
            " frames=" + surface.uniqueFrames +
            " valid=" + segments.size + "/" + segmentCount +
            " fitMissing=" + fitMissing +
            " rmseRejected=" + rmseRejected +
            " slopeRejected=" + slopeRejected

        if (segments.size < 4) {
            lastDiagnostic = prefix + " final=validSegments<4 | " +
                segmentDiagnostics.joinToString(" | ")
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
            lastDiagnostic = prefix +
                " final=medianOverflow long=" + String.format("%.2f", longitudinal) +
                " cross=" + String.format("%.2f", cross) + " | " +
                segmentDiagnostics.joinToString(" | ")
            return null
        }

        lastDiagnostic = prefix +
            " final=OK long=" + String.format("%.2f", longitudinal) +
            " cross=" + String.format("%.2f", cross) + " | " +
            segmentDiagnostics.joinToString(" | ")

        return SlopeReport(
            distanceMeters = distance,
            segments = segments,
            overallLongitudinalPercent = longitudinal,
            overallCrossPercent = cross,
            pointCount = surface.sourcePointCount
        )
    }
}
