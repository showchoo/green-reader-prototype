package jp.example.greenreader.precision

/**
 * Field quality must not declare a near-static one-view scan as 'high'
 * solely because repeated Depth frames agree with themselves.
 *
 * Camera movement and near-field parallax are necessary evidence for a
 * *high-confidence claim*, not proof of physical measurement accuracy.
 * Never changes the slope, point cloud, or line geometry.
 */
object PrecisionMotionEvidenceGate {
    private const val MIN_BASELINE_M = 0.15f

    data class Verdict(
        val insufficientBaseline: Boolean,
        val cappedFromHigh: Boolean,
        val cameraTravelMeters: Float,
        val quality: PrecisionScanQuality
    ) {
        fun diagnostic(): String =
            "MOTION_EVIDENCE travelM=" +
                String.format(java.util.Locale.US, "%.3f", cameraTravelMeters) +
                " minHighM=" + MIN_BASELINE_M +
                " insufficient=" + insufficientBaseline +
                " highCapped=" + cappedFromHigh +
                " qualityTier=" + quality.tier
    }

    fun evaluate(initial: PrecisionScanQuality): Verdict {
        val travel = initial.cameraTravelMeters
        val insufficient = !travel.isFinite() || travel < MIN_BASELINE_M
        val capHigh = insufficient &&
            initial.tier == PrecisionQualityEstimator.TIER_HIGH_PRECISION
        val quality = if (!capHigh) initial else initial.copy(
            score = initial.score.coerceAtMost(84),
            tier = PrecisionQualityEstimator.TIER_STANDARD,
            guidance = (
                listOf("端末の移動が少ないため高信頼判定を保留。床面を映したまま20〜30cmゆっくり移動してください") +
                initial.guidance
            ).distinct().take(3)
        )
        return Verdict(insufficient, capHigh, travel, quality)
    }
}
