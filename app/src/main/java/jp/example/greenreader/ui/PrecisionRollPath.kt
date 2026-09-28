package jp.example.greenreader.ui

import android.graphics.Path
import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Builds a dense visual roll path from the measured segment slopes.
 *
 * This is display-only: it never changes SlopeReport/PuttAdvisor values.
 * The AIM offset remains the main trajectory skeleton; segment cross slopes
 * only add local curvature. The curve is constrained to BALL and CUP exactly.
 */
object PrecisionRollPath {
    fun build(
        startX: Float,
        startY: Float,
        endX: Float,
        endY: Float,
        crossX: Float,
        crossY: Float,
        report: SlopeReport,
        aimOffsetPx: Float
    ): Path {
        val dx = endX - startX
        val dy = endY - startY
        val length = sqrt(dx * dx + dy * dy).coerceAtLeast(1f)

        val crossMag = sqrt(crossX * crossX + crossY * crossY).coerceAtLeast(0.001f)
        val nx = crossX / crossMag
        val ny = crossY / crossMag

        val count = max(96, report.segments.size * 24).coerceAtMost(192)
        val raw = FloatArray(count + 1)
        val dt = 1f / count
        var lateralVelocity = 0f
        var lateral = 0f

        for (i in 1..count) {
            val t = i * dt
            val meters = report.distanceMeters * t
            // Positive cross slope means downhill toward -t in the analyzer basis.
            val accel = -interpolatedCrossPercent(report, meters) / 12f
            lateralVelocity += accel * dt
            lateral += lateralVelocity * dt
            raw[i] = lateral
        }

        // Remove accumulated endpoint drift so the visual path always terminates
        // exactly at the measured Cup.
        val endDrift = raw[count]
        var maxCorrected = 0f
        val corrected = FloatArray(count + 1)
        for (i in 0..count) {
            val t = i * dt
            corrected[i] = raw[i] - endDrift * t
            maxCorrected = max(maxCorrected, abs(corrected[i]))
        }

        // Measured local break controls only a bounded detail term. AIM stays the
        // dominant curve, preventing visual overstatement of noisy segment slopes.
        val detailScale = length * 0.55f
        val maxDetail = length * 0.18f

        val xs = FloatArray(count + 1)
        val ys = FloatArray(count + 1)
        for (i in 0..count) {
            val t = i * dt
            val centerX = startX + dx * t
            val centerY = startY + dy * t
            val aimShape = (sin(PI.toFloat() * t) * aimOffsetPx * 0.52f)
            val detail = (corrected[i] * detailScale).coerceIn(-maxDetail, maxDetail)
            val offset = aimShape + detail
            xs[i] = centerX + nx * offset
            ys[i] = centerY + ny * offset
        }

        // Dense quadratic midpoint interpolation keeps the rendered line smooth
        // even when neighboring measured segments bend in opposite directions.
        return Path().apply {
            moveTo(xs[0], ys[0])
            for (i in 1 until count) {
                val midX = (xs[i] + xs[i + 1]) * 0.5f
                val midY = (ys[i] + ys[i + 1]) * 0.5f
                quadTo(xs[i], ys[i], midX, midY)
            }
            lineTo(endX, endY)
        }
    }

    private fun interpolatedCrossPercent(report: SlopeReport, meters: Float): Float {
        val segs = report.segments
        if (segs.isEmpty()) return report.overallCrossPercent
        if (segs.size == 1) return segs[0].crossPercent

        val centers = FloatArray(segs.size) { i ->
            (segs[i].startMeters + segs[i].endMeters) * 0.5f
        }
        if (meters <= centers.first()) return segs.first().crossPercent
        if (meters >= centers.last()) return segs.last().crossPercent

        for (i in 0 until segs.lastIndex) {
            val a = centers[i]
            val b = centers[i + 1]
            if (meters <= b) {
                val u = ((meters - a) / (b - a).coerceAtLeast(0.001f)).coerceIn(0f, 1f)
                return segs[i].crossPercent * (1f - u) + segs[i + 1].crossPercent * u
            }
        }
        return segs.last().crossPercent
    }
}
