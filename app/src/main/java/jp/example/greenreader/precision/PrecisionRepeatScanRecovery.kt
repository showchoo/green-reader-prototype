package jp.example.greenreader.precision

/** Pure timing / state decision for one user-requested scan after an AR pause. */
object PrecisionRepeatScanRecovery {
    enum class Decision { START, WAIT, REMARK, TIMEOUT }

    fun decide(
        tracking: PrecisionTrackingRetryPolicy.Action,
        deadlineExpired: Boolean
    ): Decision = when (tracking) {
        PrecisionTrackingRetryPolicy.Action.READY -> Decision.START
        PrecisionTrackingRetryPolicy.Action.REMARK_BALL,
        PrecisionTrackingRetryPolicy.Action.REMARK_CUP -> Decision.REMARK
        PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING ->
            if (deadlineExpired) Decision.TIMEOUT else Decision.WAIT
    }
}
