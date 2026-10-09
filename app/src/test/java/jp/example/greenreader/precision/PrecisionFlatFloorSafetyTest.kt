package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionFlatFloorSafetyTest {
    private fun quality(tier: String = PrecisionQualityEstimator.TIER_STANDARD,
                        score: Int = 84) = PrecisionScanQuality(
        score=score, tier=tier,
        estimatedSlopeUncertaintyPercent=.3f,
        validWindowCount=7,
        windowLongStdDevPercent=.2f,
        windowCrossStdDevPercent=.2f,
        medianCellMadMm=3f,
        medianLocalRmseMm=4f,
        corridorCoverage=1f,
        sourcePointCount=16000,
        uniqueDepthFrames=19,
        groundCellCount=300,
        candidateCellCount=320,
        rawAcceptedFrames=50,
        fullAcceptedFrames=0,
        duplicateDepthFrames=0,
        trackingRatio=1f,
        poseJumpCount=0,
        cameraTravelMeters=.25f,
        guidance=listOf("検証版")
    )
    private fun audit(status: PrecisionMarkerDepthHeightAudit.Status,
                      error: Float? = .062f) =
        PrecisionMarkerDepthHeightAudit.Result(
            status, 0f, error, error, 40, 40
        )

    @Test fun v93PuttFiveReversalDetected() {
        val first = Pair(-8.839f, 1.202f)
        val changed = Pair(7.435f, -3.519f)
        val v = PrecisionSamePuttAudit.evaluate(listOf(first), changed)
        assertEquals(PrecisionSamePuttAudit.Status.CONFLICT, v.status)
        assertTrue(v.signFlip)
        assertTrue(v.maxLongDifferencePp > 16f)
        assertTrue(v.blocksDirection)
    }

    @Test fun v93RepeatedWrongDirectionStillNotTrusted() {
        val v = PrecisionSamePuttAudit.evaluate(
            listOf(Pair(7.435f, -3.519f)), Pair(7.567f, -2.534f)
        )
        assertEquals(PrecisionSamePuttAudit.Status.CONSISTENT, v.status)
        val verdict = PrecisionScanConfidenceGuard.apply(
            quality(), audit(PrecisionMarkerDepthHeightAudit.Status.DISAGREEMENT), v
        )
        assertEquals(PrecisionQualityEstimator.TIER_LOW_CONFIDENCE, verdict.quality.tier)
        assertTrue(verdict.quality.score <= 59)
        assertTrue(verdict.blocksDirection)
    }

    @Test fun flatFloorFirstScanThreeCentimeterConflictNotIgnored() {
        val ball = Vec3(0f, 0f, 0f)
        val cup = Vec3(0f, -.03961f, -.64f)
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (i in 0..16) for (j in -4..4) {
            val z = -i * .04f
            val h = -.00845f * (i * .04f / .64f)
            cells += PrecisionSurfaceCell(j*.03f, z, h, .9f, 6, .001f)
        }
        val surface=PrecisionSurfaceModel(cells,.03f,15000,20,
            groundCellCount=cells.size)
        val r=PrecisionMarkerDepthHeightAudit.evaluate(surface,ball,cup)
        assertEquals(PrecisionMarkerDepthHeightAudit.Status.DISAGREEMENT,r.status)
        assertTrue(r.discrepancyMeters!! > .025f)
    }

    @Test fun noReportNeverInventsAConflict() {
        val v=PrecisionSamePuttAudit.evaluate(
            listOf(Pair(8f, 4f)), null
        )
        assertEquals(PrecisionSamePuttAudit.Status.NO_REPORT,v.status)
    }

    @Test fun genuineSlopeWithConsistentIndependentSignalsNotBlocked() {
        val v=PrecisionSamePuttAudit.evaluate(
            listOf(Pair(4.9f,1.5f)), Pair(5.1f,1.6f)
        )
        val judgment=PrecisionScanConfidenceGuard.apply(
            quality(PrecisionQualityEstimator.TIER_HIGH_PRECISION, 93),
            audit(PrecisionMarkerDepthHeightAudit.Status.CONSISTENT, .003f),v)
        assertFalse(judgment.blocksDirection)
        assertEquals(93, judgment.quality.score)
        assertEquals(PrecisionQualityEstimator.TIER_HIGH_PRECISION,judgment.quality.tier)
    }

    @Test fun insufficientCoverageCannotClaimHighConfidence() {
        val j=PrecisionScanConfidenceGuard.apply(
            quality(PrecisionQualityEstimator.TIER_HIGH_PRECISION,98),
            audit(PrecisionMarkerDepthHeightAudit.Status.INSUFFICIENT_COVERAGE,null),
            PrecisionSamePuttAudit.evaluate(emptyList(), Pair(2f,2f))
        )
        assertFalse(j.blocksDirection)
        assertEquals(PrecisionQualityEstimator.TIER_STANDARD,j.quality.tier)
        assertEquals(84,j.quality.score)
    }

    @Test fun contradictionStopsDirectionEvenForHighOriginalQuality() {
        val j=PrecisionScanConfidenceGuard.apply(
            quality(PrecisionQualityEstimator.TIER_HIGH_PRECISION,96),
            audit(PrecisionMarkerDepthHeightAudit.Status.DISAGREEMENT),
            PrecisionSamePuttAudit.evaluate(emptyList(), Pair(2f,3f))
        )
        assertTrue(j.blocksDirection)
        assertEquals(59,j.quality.score)
        assertTrue(j.quality.guidance.first().contains("高低差"))
    }

    @Test fun samePuttDeviationDoesNotHidePreviousGoodMeasurement() {
        val j=PrecisionScanConfidenceGuard.apply(
            quality(),
            audit(PrecisionMarkerDepthHeightAudit.Status.CONSISTENT,.001f),
            PrecisionSamePuttAudit.evaluate(
                listOf(Pair(0f,0f)), Pair(4.5f,0f))
        )
        assertTrue(j.blocksDirection)
        assertEquals("SAME_PUTT_DIRECTION_CONFLICT",j.reason)
    }
}
