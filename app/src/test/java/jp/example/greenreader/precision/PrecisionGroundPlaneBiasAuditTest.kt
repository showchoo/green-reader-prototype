package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionGroundPlaneBiasAuditTest {
    private fun samples(
        forwardSlope: Float,
        crossSlope: Float,
        source: String = "raw",
        outliers: Boolean = false
    ): List<PrecisionDepthPoint> {
        val pts=ArrayList<PrecisionDepthPoint>()
        for (x in -7..7) for (z in -7..7) for (t in 1..4) {
            val xx=x*0.08f
            val zz=z*0.08f
            val noise=if (t%2==0) 0.001f else -0.001f
            pts += PrecisionDepthPoint(
                xx,0.028f+crossSlope*xx+forwardSlope*zz+noise,
                zz,0.95f,t.toLong(),source
            )
            if (outliers && x%4==0 && z%4==0) {
                pts += PrecisionDepthPoint(xx,0.29f,zz,0.95f,t.toLong(),source)
            }
        }
        return pts
    }

    @Test fun horizontalFloorHasNearZeroRawSlope() {
        val f=PrecisionGroundPlaneBiasAudit.fit(samples(0f,0f),"raw")
        assertTrue(f.supported)
        assertEquals(0f,f.slopeXPct,0.1f)
        assertEquals(0f,f.slopeZPct,0.1f)
        assertEquals(0.028f,f.interceptAtBallM,0.003f)
    }

    @Test fun tiltedFloorWithClutterStillMeasuresTheDiagnosticTilt() {
        val f=PrecisionGroundPlaneBiasAudit.fit(
            samples(0.063f,0.008f,outliers=true),"raw"
        )
        assertTrue(f.supported)
        assertEquals(6.3f,f.slopeZPct,0.35f)
        assertEquals(0.8f,f.slopeXPct,0.35f)
        assertTrue(f.rmsMm<10f)
    }

    @Test fun lineLikeOrSingleFrameDataCannotBeCertified() {
        val points=List(500) {
            PrecisionDepthPoint(0.01f,0.01f,0.01f,0.95f,1L,"raw")
        }
        val f=PrecisionGroundPlaneBiasAudit.fit(points,"raw")
        assertFalse(f.supported)
        val diagnostic=PrecisionGroundPlaneBiasAudit.diagnostic(
            points,PrecisionGroundPlaneBiasAudit.PlaneObservation()
        )
        assertTrue(diagnostic.contains("rawValid=false"))
        assertTrue(diagnostic.contains("rawArTiltDisagreementPct=NA"))
        assertTrue(diagnostic.contains("arAvailable=false"))
    }

    @Test fun sourceDifferenceAndArEstimateStayObservational() {
        val both=samples(0.063f,0f,"raw")+samples(0f,0f,"full")
        val diagnostic=PrecisionGroundPlaneBiasAudit.diagnostic(
            both,
            PrecisionGroundPlaneBiasAudit.PlaneObservation(
                planeUpdates=3,trackedNearBallUpdates=2,
                available=true,slopeXPct=0f,slopeZPct=0f,
                heightAtBallM=0f
            )
        )
        assertTrue(diagnostic.contains("rawValid=true"))
        assertTrue(diagnostic.contains("fullValid=true"))
        assertTrue(diagnostic.contains("arAvailable=true"))
        assertTrue(diagnostic.contains("rawFullTiltDisagreementPct=6.30"))
        assertTrue(diagnostic.contains("groundTruth=false"))
    }

    @Test fun insufficientRawMustNotBeBackfilledWithFull() {
        val fullOnly=samples(0.065f,0f,"full")
        val diagnostic=PrecisionGroundPlaneBiasAudit.diagnostic(
            fullOnly,PrecisionGroundPlaneBiasAudit.PlaneObservation()
        )
        assertTrue(diagnostic.contains("rawValid=false"))
        assertTrue(diagnostic.contains("fullValid=true"))
        assertTrue(diagnostic.contains("rawFullTiltDisagreementPct=NA"))
    }
}
