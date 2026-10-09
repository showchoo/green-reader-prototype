package jp.example.greenreader.precision

/** Pure, fail-closed rules for recovering from ARCore tracking interruption.
 * Never assert that a lost anchor still refers to the same physical mark.
 */
object PrecisionTrackingRetryPolicy {
    enum class Action { READY, WAIT_FOR_TRACKING, REMARK_BALL, REMARK_CUP }

    fun choose(cameraTracking: Boolean, ballState: String?, cupState: String?): Action {
        // Camera tracking may recover after a brief PAUSED period.
        if (!cameraTracking) return Action.WAIT_FOR_TRACKING

        // STOPPED anchors cannot recover. Their coordinates are not a valid
        // substitute for re-tapping the original physical point.
        if (ballState == null || ballState == "STOPPED") return Action.REMARK_BALL
        if (cupState == null || cupState == "STOPPED") return Action.REMARK_CUP

        if (ballState != "TRACKING" || cupState != "TRACKING")
            return Action.WAIT_FOR_TRACKING

        return Action.READY
    }

    fun instruction(action: Action): String = when (action) {
        Action.READY -> "位置追跡が復帰しました。スキャンできます"
        Action.WAIT_FOR_TRACKING -> "位置追跡が一時停止しています。端末をゆっくり動かし、復帰後に再スキャンしてください"
        Action.REMARK_BALL -> "ボール位置の追跡が失われました。ボールとカップを設定し直してください"
        Action.REMARK_CUP -> "カップ位置の追跡が失われました。カップを設定し直してください"
    }
}
