package jp.example.greenreader.precision

/**
 * Never use a high internal repeatability score to claim high confidence
 * after physical AR-marker and accepted ground-cell height changes disagree.
 *
 * An unverified cross-check is not proof of accuracy. This gate modifies only
 * the displayed and saved quality, not the raw slope or analysis model.
 */
object PrecisionScanConfidenceGuard {
    data class Judgment(
        val blocksDirection: Boolean,
        val reason: String,
        val quality: PrecisionScanQuality
    ) {
        fun summary(): String = "TRUST_GATE reason=" + reason +
            " blockDirection=" + blocksDirection +
            " tier=" + quality.tier +
            " score=" + quality.score
    }

    fun apply(
        original: PrecisionScanQuality,
        marker: PrecisionMarkerDepthHeightAudit.Result,
        samePutt: PrecisionSamePuttAudit.Result
    ): Judgment {
        val markerContradiction =
            marker.status == PrecisionMarkerDepthHeightAudit.Status.DISAGREEMENT
        val repeatContradiction = samePutt.blocksDirection
        val insufficient =
            marker.status == PrecisionMarkerDepthHeightAudit.Status.INSUFFICIENT_COVERAGE
        val reason = when {
            markerContradiction && repeatContradiction -> "MARKER_DEPTH_AND_REPEAT_CONFLICT"
            markerContradiction -> "MARKER_DEPTH_CONFLICT"
            repeatContradiction -> "SAME_PUTT_DIRECTION_CONFLICT"
            insufficient -> "MARKER_DEPTH_UNVERIFIED"
            else -> "NO_INTERNAL_CONFLICT_DETECTED"
        }
        if (markerContradiction || repeatContradiction) {
            val instructions = buildList {
                if (markerContradiction) add(
                    "AR目印とDepthの高低差が矛盾。測定値と左右ラインを信用せず、床面を再指定してください"
                )
                if (repeatContradiction) add(
                    "同じパットの前回測定と傾斜方向・大きさが不一致。目印を確認して再測定してください"
                )
            }
            val downgraded = original.copy(
                score = original.score.coerceAtMost(59),
                tier = PrecisionQualityEstimator.TIER_LOW_CONFIDENCE,
                guidance = (instructions + original.guidance).distinct().take(3)
            )
            return Judgment(true, reason, downgraded)
        }
        if (insufficient && original.tier ==
            PrecisionQualityEstimator.TIER_HIGH_PRECISION
        ) {
            return Judgment(
                false, reason,
                original.copy(
                    score = original.score.coerceAtMost(84),
                    tier = PrecisionQualityEstimator.TIER_STANDARD,
                    guidance = (
                        listOf("目印付近のDepth地面データが不足。絶対精度は未検証です") +
                        original.guidance
                    ).distinct().take(3)
                )
            )
        }
        return Judgment(false, reason, original)
    }
}
