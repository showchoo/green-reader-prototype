package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionRepeatScanRecoveryTest {
    private val p = PrecisionRepeatScanRecovery

    @Test fun pausedCameraAfterFirstScanWaitsForFreshFrame() {
        assertEquals(p.Decision.WAIT,
            p.decide(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING, false))
    }
    @Test fun validTrackedAnchorsEnableSamePuttSecondScan() {
        assertEquals(p.Decision.START,
            p.decide(PrecisionTrackingRetryPolicy.Action.READY, false))
    }
    @Test fun permanentlyLostAnchorNeverStartsScan() {
        assertEquals(p.Decision.REMARK,
            p.decide(PrecisionTrackingRetryPolicy.Action.REMARK_BALL, false))
        assertEquals(p.Decision.REMARK,
            p.decide(PrecisionTrackingRetryPolicy.Action.REMARK_CUP, true))
    }
    @Test fun timeoutDoesNotFakeSuccess() {
        assertEquals(p.Decision.TIMEOUT,
            p.decide(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING, true))
    }
    @Test fun readyFrameAtDeadlineCanStillStart() {
        assertEquals(p.Decision.START,
            p.decide(PrecisionTrackingRetryPolicy.Action.READY, true))
    }
}
