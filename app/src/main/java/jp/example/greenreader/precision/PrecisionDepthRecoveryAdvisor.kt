package jp.example.greenreader.precision

/**
 * Depth recovery is not the same thing as camera TRACKING recovery.
 *
 * Two complete no-image scans (Raw AND Full unavailable) may warrant
 * offering a fresh ARCore Session. A fresh Session invalidates old markers;
 * restarting is NEVER automatic and must be approved by the user.
 *
 * Only terminal scan results update this state. Intermediate scan windows do
 * not count as repeated user measurements.
 */
object PrecisionDepthRecoveryAdvisor {
    data class Decision(
        val consecutiveNoDepthScans: Int,
        val terminal: Boolean,
        val offerRestart: Boolean,
        val guidance: String
    ) {
        fun diagnostic(): String =
            "DEPTH_RECOVERY_V1 terminal=" + terminal +
            " consecutiveNoImages=" + consecutiveNoDepthScans +
            " offerRestart=" + offerRestart +
            " cause=" + guidance
    }

    fun evaluate(
        previousNoDepthScans: Int,
        state: PrecisionDepthStallPolicy.State,
        terminal: Boolean
    ): Decision {
        val count = if (!terminal) previousNoDepthScans.coerceAtLeast(0)
            else if (state == PrecisionDepthStallPolicy.State.NO_DEPTH_IMAGES)
                (previousNoDepthScans.coerceAtLeast(0) + 1).coerceAtMost(99)
            else 0
        val offer = terminal &&
            state == PrecisionDepthStallPolicy.State.NO_DEPTH_IMAGES &&
            count >= 2
        val guidance = when {
            !terminal -> "OBSERVING_WINDOW"
            state == PrecisionDepthStallPolicy.State.NO_DEPTH_IMAGES ->
                "AR_TRACKING_WITHOUT_RAW_OR_FULL"
            state == PrecisionDepthStallPolicy.State.NO_USABLE_DEPTH ->
                "DEPTH_IMAGES_WITHOUT_USABLE_POINTS"
            state == PrecisionDepthStallPolicy.State.HEALTHY ->
                "IMAGES_ACQUIRED"
            else -> "OBSERVING"
        }
        return Decision(count, terminal, offer, guidance)
    }
}
