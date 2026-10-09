package jp.example.greenreader.precision

/**
 * Conservative fail-closed diagnostic for repeated depth acquisition loss.
 *
 * "Image acquired" is not the same as "usable points accepted"; this check
 * tracks both independently. A normal / recently resumed camera receives at
 * least two measurement windows before a no-depth decision.
 *
 * Never estimates an absent slope or conflates tracking with depth support.
 */
object PrecisionDepthStallPolicy {
    enum class State { OBSERVING, HEALTHY, NO_DEPTH_IMAGES, NO_USABLE_DEPTH }
    data class Decision(
        val state: State,
        val windows: Int,
        val attempts: Int,
        val rawImages: Int,
        val fullImages: Int,
        val rawAccepted: Int,
        val fullAccepted: Int,
        val notYet: Int,
        val errors: Int
    ) {
        val abortEarly: Boolean
            get() = state == State.NO_DEPTH_IMAGES || state == State.NO_USABLE_DEPTH
        fun diagnostic(): String =
            "DEPTH_HEALTH state=" + state +
            " windows=" + windows +
            " attempts=" + attempts +
            " rawImages=" + rawImages +
            " fullImages=" + fullImages +
            " rawAccepted=" + rawAccepted +
            " fullAccepted=" + fullAccepted +
            " notYet=" + notYet +
            " errors=" + errors
    }

    fun evaluate(
        total: PrecisionDepthCollector.DiagnosticsSnapshot,
        completedWindows: Int
    ): Decision {
        val windows = completedWindows.coerceAtLeast(0)
        val state = when {
            windows < 2 || total.attemptedFrames < 60 -> State.OBSERVING
            total.rawAcceptedFrames > 0 || total.fullAcceptedFrames > 0 -> State.HEALTHY
            total.rawAcquiredFrames == 0 && total.fullAcquiredFrames == 0 ->
                State.NO_DEPTH_IMAGES
            else -> State.NO_USABLE_DEPTH
        }
        return Decision(
            state = state,
            windows = windows,
            attempts = total.attemptedFrames,
            rawImages = total.rawAcquiredFrames,
            fullImages = total.fullAcquiredFrames,
            rawAccepted = total.rawAcceptedFrames,
            fullAccepted = total.fullAcceptedFrames,
            notYet = total.notYetAvailableCount,
            errors = total.otherErrorCount
        )
    }
}
