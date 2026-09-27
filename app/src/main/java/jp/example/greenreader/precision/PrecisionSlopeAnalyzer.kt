package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.SlopeSegment
import jp.example.greenreader.analysis.Vec3
import kotlin.math.sqrt

object PrecisionSlopeAnalyzer {
    fun analyze(
        surface: PrecisionSurfaceModel,
        ball: Vec3,
        cup: Vec3,
        segmentCount: Int = 8
    ): SlopeReport? {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val distance = sqrt(dx * dx + dz * dz)
        if (distance < 0.4f || surface.cells.size < 30) return null
        val fx = dx / distance
        val fz = dz / distance
        val rx = -fz
        val rz = fx

        val segments = ArrayList<SlopeSegment>()
        for (i in 0 until segmentCount) {
            val t = (i + 0.5f) / segmentCount
            val cx = ball.x + dx * t
            val cz = ball.z + dz * t
            val fit = PrecisionLocalQuadraticFitter.fit(
                surface.cells, cx, cz, fx, fz, rx, rz
            ) ?: continue
            val forward = (fit.dHdForward * 100.0).toFloat()
            val right = (fit.dHdRight * 100.0).toFloat()
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
        if (segments.size < 4) return null

        fun median(values: List<Float>): Float {
            val s = values.sorted()
            val m = s.size / 2
            return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) * 0.5f
        }

        return SlopeReport(
            distanceMeters = distance,
            segments = segments,
            overallLongitudinalPercent = median(segments.map { it.longitudinalPercent }),
            overallCrossPercent = median(segments.map { it.crossPercent }),
            pointCount = surface.sourcePointCount
        )
    }
}
