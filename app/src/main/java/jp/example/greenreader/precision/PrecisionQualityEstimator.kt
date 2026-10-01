package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.Vec3
import kotlin.math.max
import kotlin.math.sqrt

data class PrecisionScanQuality(
    val score: Int,
    val tier: String,
    val estimatedSlopeUncertaintyPercent: Float,
    val validWindowCount: Int,
    val windowLongStdDevPercent: Float,
    val windowCrossStdDevPercent: Float,
    val medianCellMadMm: Float,
    val medianLocalRmseMm: Float,
    val corridorCoverage: Float,
    val sourcePointCount: Int,
    val uniqueDepthFrames: Int,
    val groundCellCount: Int,
    val candidateCellCount: Int,
    val rawAcceptedFrames: Int,
    val fullAcceptedFrames: Int,
    val duplicateDepthFrames: Int,
    val trackingRatio: Float,
    val poseJumpCount: Int,
    val cameraTravelMeters: Float,
    val guidance: List<String>
) {
    fun summary(): String {
        val uncertainty = if (estimatedSlopeUncertaintyPercent.isFinite()) {
            String.format("%.2f", estimatedSlopeUncertaintyPercent)
        } else "-"
        return "score=$score tier=$tier uncertainty=±$uncertainty% " +
            "windows=$validWindowCount coverage=" + String.format("%.0f", corridorCoverage * 100f) + "% " +
            "rmseMm=" + String.format("%.1f", medianLocalRmseMm) +
            " cellMadMm=" + String.format("%.1f", medianCellMadMm) +
            " tracking=" + String.format("%.0f", trackingRatio * 100f) + "% " +
            "jumps=$poseJumpCount"
    }
}

/**
 * Converts raw scan diagnostics into a conservative, user-facing confidence
 * estimate. The score is deliberately based on measured data quality rather
 * than a hard-coded phone model list.
 */
object PrecisionQualityEstimator {
    const val TIER_HIGH_PRECISION = "HIGH_PRECISION"
    const val TIER_STANDARD = "STANDARD"
    const val TIER_LOW_CONFIDENCE = "LOW_CONFIDENCE"

    fun evaluate(
        surface: PrecisionSurfaceModel?,
        report: SlopeReport?,
        windowReports: List<SlopeReport>,
        collectorWindows: List<PrecisionDepthCollector.DiagnosticsSnapshot>,
        tracking: PrecisionTrackingMonitor.Snapshot,
        ball: Vec3,
        cup: Vec3
    ): PrecisionScanQuality {
        val collector = PrecisionDepthCollector.DiagnosticsSnapshot.aggregate(collectorWindows)
        val cells = surface?.cells.orEmpty()

        val medianCellMadMm = median(cells.map { it.madMeters * 1000f })
        val fitStats = localFitStats(surface, ball, cup)
        val medianLocalRmseMm = median(fitStats.map { it.rmseMeters.toFloat() * 1000f })
        val corridorCoverage = (fitStats.size / 8f).coerceIn(0f, 1f)

        val longStd = stdDev(windowReports.map { it.overallLongitudinalPercent })
        val crossStd = stdDev(windowReports.map { it.overallCrossPercent })
        val agreementSpread = max(
            if (longStd.isFinite()) longStd else 0.65f,
            if (crossStd.isFinite()) crossStd else 0.65f
        )

        val pointScore = unit(surface?.sourcePointCount?.toFloat()?.div(10000f) ?: 0f)
        val frameScore = unit(collector.acceptedUniqueFrames / 15f)
        val groundScore = unit((surface?.groundCellCount ?: 0) / 150f)
        val coverageScore = corridorCoverage
        val residualScore = if (medianLocalRmseMm.isFinite()) {
            1f - unit((medianLocalRmseMm - 5f) / 30f)
        } else 0f
        val agreementScore = if (windowReports.size >= 2) {
            1f - unit(agreementSpread / 1.0f)
        } else {
            0.55f
        }
        val trackingScore = unit(tracking.trackingRatio) *
            (1f - (tracking.poseJumpCount / 3f).coerceIn(0f, 0.65f))
        val movementScore = unit(tracking.cameraTravelMeters / 0.25f)

        val weighted =
            0.10f * pointScore +
            0.12f * frameScore +
            0.14f * groundScore +
            0.18f * coverageScore +
            0.18f * residualScore +
            0.16f * agreementScore +
            0.08f * trackingScore +
            0.04f * movementScore
        val score = (weighted * 100f).toInt().coerceIn(0, 100)

        val distance = distance(ball, cup)
        val residualUncertainty = if (medianLocalRmseMm.isFinite()) {
            // Convert surface residual into a conservative slope-scale term.
            // It is not presented as a formal 95% CI; it is an engineering
            // uncertainty estimate used for quality gating.
            val baseline = max(0.50f, distance * 0.50f)
            (medianLocalRmseMm / 1000f) / baseline * 100f * 0.20f
        } else 1.2f
        val repeatabilityUncertainty = if (windowReports.size >= 2) agreementSpread else 0.80f
        val uncertainty = max(residualUncertainty, repeatabilityUncertainty)
            .coerceIn(0.05f, 3.0f)

        val tier = when {
            score >= 85 && uncertainty <= 0.40f && corridorCoverage >= 0.875f ->
                TIER_HIGH_PRECISION
            score >= 65 && uncertainty <= 0.80f && corridorCoverage >= 0.625f ->
                TIER_STANDARD
            else -> TIER_LOW_CONFIDENCE
        }

        val guidance = buildGuidance(
            surface = surface,
            collector = collector,
            tracking = tracking,
            corridorCoverage = corridorCoverage,
            medianLocalRmseMm = medianLocalRmseMm,
            agreementSpread = agreementSpread,
            report = report
        )

        return PrecisionScanQuality(
            score = score,
            tier = tier,
            estimatedSlopeUncertaintyPercent = uncertainty,
            validWindowCount = windowReports.size,
            windowLongStdDevPercent = longStd,
            windowCrossStdDevPercent = crossStd,
            medianCellMadMm = medianCellMadMm,
            medianLocalRmseMm = medianLocalRmseMm,
            corridorCoverage = corridorCoverage,
            sourcePointCount = surface?.sourcePointCount ?: 0,
            uniqueDepthFrames = collector.acceptedUniqueFrames,
            groundCellCount = surface?.groundCellCount ?: 0,
            candidateCellCount = surface?.candidateCellCount ?: 0,
            rawAcceptedFrames = collector.rawAcceptedFrames,
            fullAcceptedFrames = collector.fullAcceptedFrames,
            duplicateDepthFrames = collector.duplicateRawFrames + collector.duplicateFullFrames,
            trackingRatio = tracking.trackingRatio,
            poseJumpCount = tracking.poseJumpCount,
            cameraTravelMeters = tracking.cameraTravelMeters,
            guidance = guidance
        )
    }

    private fun localFitStats(
        surface: PrecisionSurfaceModel?,
        ball: Vec3,
        cup: Vec3
    ): List<PrecisionLocalQuadraticFitter.Fit> {
        if (surface == null || surface.cells.isEmpty()) return emptyList()
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val distance = sqrt(dx * dx + dz * dz)
        if (distance < 0.4f) return emptyList()
        val fx = dx / distance
        val fz = dz / distance
        val rx = -fz
        val rz = fx

        val out = ArrayList<PrecisionLocalQuadraticFitter.Fit>(8)
        for (i in 0 until 8) {
            val t = (i + 0.5f) / 8f
            val cx = ball.x + dx * t
            val cz = ball.z + dz * t
            PrecisionLocalQuadraticFitter.fit(
                surface.cells, cx, cz, fx, fz, rx, rz, radiusMeters = 0.32f
            )?.let(out::add)
        }
        return out
    }

    private fun buildGuidance(
        surface: PrecisionSurfaceModel?,
        collector: PrecisionDepthCollector.DiagnosticsSnapshot,
        tracking: PrecisionTrackingMonitor.Snapshot,
        corridorCoverage: Float,
        medianLocalRmseMm: Float,
        agreementSpread: Float,
        report: SlopeReport?
    ): List<String> {
        val out = ArrayList<String>(4)
        if (collector.rawAcceptedFrames == 0 && collector.fullAcceptedFrames > 0) {
            out += "Raw Depthが少ないためFull Depthで補完しました。端末をゆっくり左右に動かすと改善する場合があります"
        }
        if (tracking.cameraTravelMeters < 0.15f) {
            out += "端末をグリーンに向けたまま左右へ20〜30cmほどゆっくり動かしてください"
        }
        if (tracking.poseJumpCount > 0 || tracking.trackingRatio < 0.92f) {
            out += "AR追跡が不安定です。急に振らず、芝と周辺の特徴が少し入る向きで再スキャンしてください"
        }
        if (corridorCoverage < 0.75f || (surface?.groundCellCount ?: 0) < 80) {
            out += "ボールからカップまでの芝面全体が入るようにスキャンしてください"
        }
        if (medianLocalRmseMm.isFinite() && medianLocalRmseMm > 25f) {
            out += "芝面のばらつきが大きいです。靴・クラブ・強い影などを画面から外してください"
        }
        if (agreementSpread.isFinite() && agreementSpread > 0.80f) {
            out += "複数測定の傾斜値が一致していません。同じ範囲をもう一度ゆっくりスキャンしてください"
        }
        if (report == null) {
            out += "傾斜解析が成立していません。ボールとカップ位置を確認して再スキャンしてください"
        }
        return out.distinct().take(3)
    }

    private fun stdDev(values: List<Float>): Float {
        if (values.size < 2) return Float.NaN
        val mean = values.average()
        val variance = values.sumOf { v ->
            val d = v.toDouble() - mean
            d * d
        } / (values.size - 1).toDouble()
        return sqrt(variance).toFloat()
    }

    private fun median(values: List<Float>): Float {
        val finite = values.filter { it.isFinite() }.sorted()
        if (finite.isEmpty()) return Float.NaN
        val m = finite.size / 2
        return if (finite.size % 2 == 1) finite[m] else (finite[m - 1] + finite[m]) * 0.5f
    }

    private fun distance(a: Vec3, b: Vec3): Float {
        val dx = b.x - a.x
        val dz = b.z - a.z
        return sqrt(dx * dx + dz * dz)
    }

    private fun unit(v: Float): Float = v.coerceIn(0f, 1f)
}
