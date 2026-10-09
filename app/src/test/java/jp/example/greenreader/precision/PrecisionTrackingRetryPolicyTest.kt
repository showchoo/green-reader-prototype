package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionTrackingRetryPolicyTest {
    private val policy = PrecisionTrackingRetryPolicy

    @Test fun stableTrackingAllowsScan() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.READY,
            policy.choose(true,"TRACKING","TRACKING"))
    }

    @Test fun pausedCameraWaitsWithoutDiscardingAnchors() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING,
            policy.choose(false,"TRACKING","TRACKING"))
    }

    @Test fun temporarilyPausedAnchorCanRecoverWithoutRetapping() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING,
            policy.choose(true,"PAUSED","TRACKING"))
        assertEquals(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING,
            policy.choose(true,"TRACKING","PAUSED"))
    }

    @Test fun stoppedBallRequiresCompleteRemarking() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.REMARK_BALL,
            policy.choose(true,"STOPPED","TRACKING"))
    }

    @Test fun stoppedCupRequiresCupRemarking() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.REMARK_CUP,
            policy.choose(true,"TRACKING","STOPPED"))
    }

    @Test fun missingAnchorsCannotSilentlyReuseOldPositions() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.REMARK_BALL,
            policy.choose(true,null,"TRACKING"))
        assertEquals(PrecisionTrackingRetryPolicy.Action.REMARK_CUP,
            policy.choose(true,"TRACKING",null))
    }

    @Test fun unknownTrackingStateIsNeverTreatedAsValid() {
        assertEquals(PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING,
            policy.choose(true,"UNKNOWN","TRACKING"))
    }

    @Test fun actionMessagesGiveMeaningfulGuidance() {
        assertEquals(true,policy.instruction(
            PrecisionTrackingRetryPolicy.Action.REMARK_BALL).contains("ボール"))
        assertEquals(true,policy.instruction(
            PrecisionTrackingRetryPolicy.Action.WAIT_FOR_TRACKING).contains("一時停止"))
    }
}
