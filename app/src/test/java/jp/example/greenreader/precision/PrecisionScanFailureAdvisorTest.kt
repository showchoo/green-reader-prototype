package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class PrecisionScanFailureAdvisorTest {
    private fun q(
        raw: Int, full: Int, ground: Int, windows: Int,
        travel: Float = .05f
    ) = PrecisionScanQuality(
        score = 45,
        tier = PrecisionQualityEstimator.TIER_LOW_CONFIDENCE,
        estimatedSlopeUncertaintyPercent = 1.2f,
        validWindowCount = windows,
        windowLongStdDevPercent = Float.NaN,
        windowCrossStdDevPercent = Float.NaN,
        medianCellMadMm = 25f,
        medianLocalRmseMm = Float.NaN,
        corridorCoverage = 0f,
        sourcePointCount = 90000,
        uniqueDepthFrames = raw + full,
        groundCellCount = ground,
        candidateCellCount = ground+5,
        rawAcceptedFrames = raw,
        fullAcceptedFrames = full,
        duplicateDepthFrames = full,
        trackingRatio = 1f,
        poseJumpCount = 0,
        cameraTravelMeters = travel,
        guidance = emptyList()
    )
    @Test fun v96Putt4FailsFromFullDepthAndInsufficientGround() {
        val a = PrecisionScanFailureAdvisor.evaluate(q(0,141,58,0,.044f))
        assertEquals(PrecisionScanFailureAdvisor.Reason.FULL_DEPTH_WITHOUT_GROUND,a.reason)
        assertTrue(a.message().contains("床面"))
        assertTrue(a.diagnostic().contains("FAILURE_ADVICE"))
    }
    @Test fun v96Putt3HasRawButLacksValidLocalFits() {
        val a = PrecisionScanFailureAdvisor.evaluate(q(153,0,102,0,.034f))
        assertEquals(PrecisionScanFailureAdvisor.Reason.NO_VALID_LOCAL_FITS,a.reason)
    }
    @Test fun v96Putt2MostlyFullDepthAndNoValidFits() {
        val a = PrecisionScanFailureAdvisor.evaluate(q(9,127,161,0,.043f))
        assertEquals(PrecisionScanFailureAdvisor.Reason.MOSTLY_FULL_DEPTH_WITH_NO_VALID_FITS,a.reason)
    }
    @Test fun noReportCannotBecomeSuccess() {
        val a=PrecisionScanFailureAdvisor.evaluate(null)
        assertEquals(PrecisionScanFailureAdvisor.Reason.NO_QUALITY_EVIDENCE,a.reason)
        assertTrue(a.message().contains("確定できません"))
    }
    @Test fun lowParallaxWithSomeWindowDataGetsSpecificGuidance() {
        val a=PrecisionScanFailureAdvisor.evaluate(q(10,120,180,2,.03f))
        assertEquals(PrecisionScanFailureAdvisor.Reason.TOO_LITTLE_PARALLAX,a.reason)
    }
    @Test fun enoughMovementButNoRepeatMatch() {
        val a=PrecisionScanFailureAdvisor.evaluate(q(95,0,220,2,.28f))
        assertEquals(PrecisionScanFailureAdvisor.Reason.NOT_ENOUGH_VALID_WINDOWS,a.reason)
    }
}
