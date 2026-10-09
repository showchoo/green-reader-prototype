package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class PrecisionMotionEvidenceGateTest {
    private fun quality(score: Int, tier: String, travel: Float) =
        PrecisionScanQuality(
            score = score,
            tier = tier,
            estimatedSlopeUncertaintyPercent = .22f,
            validWindowCount = 7,
            windowLongStdDevPercent = .10f,
            windowCrossStdDevPercent = .10f,
            medianCellMadMm = 3f,
            medianLocalRmseMm = 4f,
            corridorCoverage = 1f,
            sourcePointCount = 40000,
            uniqueDepthFrames = 60,
            groundCellCount = 300,
            candidateCellCount = 350,
            rawAcceptedFrames = 55,
            fullAcceptedFrames = 0,
            duplicateDepthFrames = 0,
            trackingRatio = 1f,
            poseJumpCount = 0,
            cameraTravelMeters = travel,
            guidance = emptyList()
        )

    @Test fun m07PuttThreeRawOnlyButThreeCmTravelNotHigh() {
        val p = PrecisionMotionEvidenceGate.evaluate(
            quality(94, PrecisionQualityEstimator.TIER_HIGH_PRECISION, .03f)
        )
        assertTrue(p.insufficientBaseline)
        assertTrue(p.cappedFromHigh)
        assertEquals(PrecisionQualityEstimator.TIER_STANDARD, p.quality.tier)
        assertEquals(84, p.quality.score)
        assertTrue(p.quality.guidance.first().contains("20〜30cm"))
    }

    @Test fun adequateTravelDoesNotProveAccuracyOrArtificiallyRaiseTier() {
        val p = PrecisionMotionEvidenceGate.evaluate(
            quality(94, PrecisionQualityEstimator.TIER_HIGH_PRECISION, .22f)
        )
        assertFalse(p.insufficientBaseline)
        assertFalse(p.cappedFromHigh)
        assertEquals(94, p.quality.score)
    }

    @Test fun alreadyLowQualityRemainsLowWithoutManipulation() {
        val p = PrecisionMotionEvidenceGate.evaluate(
            quality(59, PrecisionQualityEstimator.TIER_LOW_CONFIDENCE, .03f)
        )
        assertTrue(p.insufficientBaseline)
        assertFalse(p.cappedFromHigh)
        assertEquals(59, p.quality.score)
        assertEquals(PrecisionQualityEstimator.TIER_LOW_CONFIDENCE, p.quality.tier)
    }

    @Test fun exactThresholdAndMissingBaseline() {
        val exact=PrecisionMotionEvidenceGate.evaluate(
            quality(92, PrecisionQualityEstimator.TIER_HIGH_PRECISION, .15f)
        )
        assertFalse(exact.cappedFromHigh)
        val missing=PrecisionMotionEvidenceGate.evaluate(
            quality(92, PrecisionQualityEstimator.TIER_HIGH_PRECISION, Float.NaN)
        )
        assertTrue(missing.cappedFromHigh)
    }
}
