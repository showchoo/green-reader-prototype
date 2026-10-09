package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class PrecisionDepthStallPolicyTest {
    private fun snap(
        attempts: Int, raw: Int, full: Int, rawImages: Int = raw,
        fullImages: Int = full, notYet: Int = 0
    ) = PrecisionDepthCollector.DiagnosticsSnapshot(
        attemptedFrames = attempts,
        rawAcquiredFrames = rawImages,
        fullAcquiredFrames = fullImages,
        rawAcceptedFrames = raw,
        fullAcceptedFrames = full,
        acceptedUniqueFrames = raw + full,
        notYetAvailableCount = notYet
    )
    @Test fun latestM07RepeatedTrackingButNoDepthFailsEarly() {
        val v = PrecisionDepthStallPolicy.evaluate(snap(84,0,0,0,0,168),2)
        assertEquals(PrecisionDepthStallPolicy.State.NO_DEPTH_IMAGES,v.state)
        assertTrue(v.abortEarly)
        assertTrue(v.diagnostic().contains("rawAccepted=0"))
    }
    @Test fun warmupDoesNotAbortEarlyEvenWhenNoDepthYet() {
        val v = PrecisionDepthStallPolicy.evaluate(snap(90,0,0),1)
        assertEquals(PrecisionDepthStallPolicy.State.OBSERVING,v.state)
        assertFalse(v.abortEarly)
    }
    @Test fun fewerThanSixtyAttemptsAllowsTimeToConverge() {
        val v = PrecisionDepthStallPolicy.evaluate(snap(53,0,0),3)
        assertEquals(PrecisionDepthStallPolicy.State.OBSERVING,v.state)
    }
    @Test fun imagesWithoutUsablePointsNotMisreportedAsNeverAcquired() {
        val v = PrecisionDepthStallPolicy.evaluate(snap(93,0,0,12,30),2)
        assertEquals(PrecisionDepthStallPolicy.State.NO_USABLE_DEPTH,v.state)
        assertTrue(v.abortEarly)
    }
    @Test fun FullDepthRecoveryAfterRawFailureKeepsScanning() {
        val v = PrecisionDepthStallPolicy.evaluate(snap(120,0,5,0,90),3)
        assertEquals(PrecisionDepthStallPolicy.State.HEALTHY,v.state)
        assertFalse(v.abortEarly)
    }
    @Test fun rawEvidenceKeepsHealthyEvenIfFullDepthIsUnavailable() {
        val v = PrecisionDepthStallPolicy.evaluate(snap(90,8,0),2)
        assertEquals(PrecisionDepthStallPolicy.State.HEALTHY,v.state)
    }
    @Test fun noDataAdvisorPrioritizesDepthCause() {
        val d = PrecisionDepthStallPolicy.evaluate(snap(90,0,0,0,0,100),2)
        val a = PrecisionScanFailureAdvisor.evaluate(null,d)
        assertEquals(PrecisionScanFailureAdvisor.Reason.NO_DEPTH_IMAGES,a.reason)
        assertTrue(a.message().contains("AR・Depth再起動"))
    }
}
