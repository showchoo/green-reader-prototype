package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionDepthRecoveryAdvisorTest {
    private val noImages=PrecisionDepthStallPolicy.State.NO_DEPTH_IMAGES
    private val healthy=PrecisionDepthStallPolicy.State.HEALTHY

    @Test fun windowsDoNotPretendToBeDistinctCompleteScans() {
        val window=PrecisionDepthRecoveryAdvisor.evaluate(0,noImages,false)
        assertEquals(0,window.consecutiveNoDepthScans)
        assertFalse(window.offerRestart)
        assertFalse(window.terminal)
    }

    @Test fun firstNoDepthScanDoesNotRestartOrNag() {
        val first=PrecisionDepthRecoveryAdvisor.evaluate(0,noImages,true)
        assertEquals(1,first.consecutiveNoDepthScans)
        assertFalse(first.offerRestart)
        assertTrue(first.diagnostic().contains("AR_TRACKING_WITHOUT_RAW_OR_FULL"))
    }

    @Test fun secondConsecutiveCompleteNoDepthScanOffersOptInOnly() {
        val second=PrecisionDepthRecoveryAdvisor.evaluate(1,noImages,true)
        assertEquals(2,second.consecutiveNoDepthScans)
        assertTrue(second.offerRestart)
        assertTrue(second.terminal)
    }

    @Test fun workingDepthOrDifferentFailureResetsNoImageStreak() {
        val recovered=PrecisionDepthRecoveryAdvisor.evaluate(2,healthy,true)
        assertEquals(0,recovered.consecutiveNoDepthScans)
        assertFalse(recovered.offerRestart)
        val unusable=PrecisionDepthRecoveryAdvisor.evaluate(
            2,PrecisionDepthStallPolicy.State.NO_USABLE_DEPTH,true
        )
        assertEquals(0,unusable.consecutiveNoDepthScans)
        assertFalse(unusable.offerRestart)
    }
}
