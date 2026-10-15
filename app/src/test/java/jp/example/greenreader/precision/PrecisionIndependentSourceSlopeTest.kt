package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionIndependentSourceSlopeTest {
    @Test fun independentRawAndFullLongitudinalFitIsPersistedWithDirection() {
        val raw=PrecisionDepthSourceAudit.Estimate(
            crossPercent=-1.2f,points=7200,uniqueFrames=17,
            groundCells=87,rmseMm=7.1f,longitudinalPercent=-1.39f
        )
        val full=PrecisionDepthSourceAudit.Estimate(
            crossPercent=0.2f,points=9900,uniqueFrames=39,
            groundCells=120,rmseMm=11.2f,longitudinalPercent=4.25f
        )
        val report=PrecisionDepthSourceAudit.Verdict(
            reason="SOURCE_FIT_UNRESOLVED",blocksDirection=true,
            crossSourceVerified=false,raw=raw,full=full
        ).diagnostic
        assertTrue(report.contains("INDEPENDENT_SOURCE_SLOPES_V1"))
        assertTrue(report.contains("rawLongPct=-1.39"))
        assertTrue(report.contains("fullLongPct=4.25"))
        assertTrue(report.contains("deltaLongPp=5.64"))
        assertTrue(report.contains("rawCrossPct=-1.20"))
        assertTrue(report.contains("fullCrossPct=0.20"))
        assertTrue(report.contains("independentGroundTruth=false"))
    }

    @Test fun missingSecondSourceRemainsUndeterminedNotAgreement() {
        val raw=PrecisionDepthSourceAudit.Estimate(
            crossPercent=-2.5f,points=9500,uniqueFrames=40,
            groundCells=109,rmseMm=6f,longitudinalPercent=6.3f
        )
        val full=PrecisionDepthSourceAudit.Estimate(null,0,0,0,null)
        val verdict=PrecisionDepthSourceAudit.Verdict(
            reason="INSUFFICIENT_DUAL_SOURCE",blocksDirection=false,
            crossSourceVerified=false,raw=raw,full=full
        )
        assertFalse(verdict.crossSourceVerified)
        assertTrue(verdict.diagnostic.contains("rawLongPct=6.30"))
        assertTrue(verdict.diagnostic.contains("fullLongPct=NA"))
        assertTrue(verdict.diagnostic.contains("deltaLongPp=NA"))
    }

    @Test fun establishedVetoPolicyForCrossSlopeDoesNotChange() {
        val opposed=PrecisionDepthSourceAudit.judge(
            reportedCross=2f,rawCross=2f,fullCross=-2f,
            rawPoints=10000,fullPoints=10000,
            rawFrames=20,fullFrames=20
        )
        assertEquals("OPPOSITE_RAW_FULL",opposed.reason)
        assertTrue(opposed.blocksDirection)
        val missing=PrecisionDepthSourceAudit.judge(
            reportedCross=2f,rawCross=2f,fullCross=null,
            rawPoints=10000,fullPoints=0,
            rawFrames=20,fullFrames=0
        )
        assertEquals("INSUFFICIENT_DUAL_SOURCE",missing.reason)
        assertFalse(missing.crossSourceVerified)
    }
}
