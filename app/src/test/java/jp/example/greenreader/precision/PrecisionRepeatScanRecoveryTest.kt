package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionRepeatScanRecoveryTest {
    private val p = PrecisionRepeatScanRecovery

    @Test fun pausedCameraAfterFirstScanWaitsForFreshFrame() {
        assertEquals(PrecisionRepeatScanRecovery.Decision.WAIT,
            p.decide(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING, false))
    }
    @Test fun validTrackedAnchorsEnableSamePuttSecondScan() {
        assertEquals(PrecisionRepeatScanRecovery.Decision.START,
            p.decide(PrecisionTrackingRetryPolicy.Action.READY, false))
    }
    @Test fun permanentlyLostAnchorNeverStartsScan() {
        assertEquals(PrecisionRepeatScanRecovery.Decision.REMARK,
            p.decide(PrecisionTrackingRetryPolicy.Action.REMARK_BALL, false))
        assertEquals(PrecisionRepeatScanRecovery.Decision.REMARK,
            p.decide(PrecisionTrackingRetryPolicy.Action.REMARK_CUP, true))
    }
    @Test fun timeoutDoesNotFakeSuccess() {
        assertEquals(PrecisionRepeatScanRecovery.Decision.TIMEOUT,
            p.decide(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING, true))
    }
    @Test fun readyFrameAtDeadlineCanStillStart() {
        assertEquals(PrecisionRepeatScanRecovery.Decision.START,
            p.decide(PrecisionTrackingRetryPolicy.Action.READY, true))
    }
}
