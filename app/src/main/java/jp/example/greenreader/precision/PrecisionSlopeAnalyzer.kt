package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.SlopeSegment
import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.sqrt
import kotlin.math.max

object PrecisionSlopeAnalyzer {
    private const val MAX_USABLE_SLOPE_PERCENT = 12f
    private const val MAX_LOCAL_RMSE_METERS = 0.040
    private const val LOCAL_FIT_RADIUS_METERS = 0.32f

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

        // Establish one robust corridor-wide reference plane first. Full Depth can
        // contain a smooth range-dependent bow that looks like a large local slope
        // even when every individual fit has a decent RMSE. A real putting surface
        // should not change by tens of percentage points over a few decimetres, so
        // local fits are validated against this large-scale reference.
        val globalFitRadius = max(0.60f, distance * 0.75f)
        val globalFit = PrecisionLocalQuadraticFitter.fit(
            surface.cells,
            ball.x + dx * 0.5f,
            ball.z + dz * 0.5f,
            fx, fz, rx, rz,
            radiusMeters = globalFitRadius
        )
        val globalForward = globalFit?.let { (it.dHdForward * 100.0).toFloat() }
        val globalRight = globalFit?.let { (it.dHdRight * 100.0).toFloat() }
        val globalTotal = if (globalForward != null && globalRight != null) {
            sqrt(globalForward * globalForward + globalRight * globalRight)
        } else Float.NaN

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
            val rawForward = (fit.dHdForward * 100.0).toFloat()
            val rawRight = (fit.dHdRight * 100.0).toFloat()

            // If a local derivative departs dramatically from the corridor-wide
            // plane, treat it as Depth bow / edge geometry rather than a physical
            // green break. Keep modest local variation, but cap the deviation.
            val maxLocalDeltaPercent = 5.0f
            val forward = if (globalForward != null && globalForward.isFinite()) {
                rawForward.coerceIn(globalForward - maxLocalDeltaPercent, globalForward + maxLocalDeltaPercent)
            } else rawForward
            val right = if (globalRight != null && globalRight.isFinite()) {
                rawRight.coerceIn(globalRight - maxLocalDeltaPercent, globalRight + maxLocalDeltaPercent)
            } else rawRight
            val total = sqrt(forward * forward + right * right)
            if (total.isFinite() && total > maxSeenSlope) maxSeenSlope = total

            val values =
                "n=${fit.samples} rmse=" + String.format("%.3f", fit.rmseMeters) +
                " rawF=" + String.format("%.1f", rawForward) + "%" +
                " rawR=" + String.format("%.1f", rawRight) + "%" +
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
            " global=" + if (globalForward != null && globalRight != null) {
                String.format("%.1f/%.1f/%.1f", globalForward, globalRight, globalTotal)
            } else "null" +
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
