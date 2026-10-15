package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionRawFloorCoveragePolicyTest {
    private fun raw(along: Float, across: Float, y: Float): PrecisionDepthPoint =
        PrecisionDepthPoint(across,y,-along,0.95f,100L,"raw")

    private fun floorPoints(): List<PrecisionDepthPoint> =
        (0..9).flatMap { i ->
            (0..9).map { j ->
                raw(i*0.10f,(j-5)*0.028f,0.014f)
            }
        }
    private val cup = floatArrayOf(0f,0f,-1.0f)

    @Test fun broadRawFloorCoveragePassesForOrdinaryOneMeterPutt() {
        val evidence=PrecisionRawFloorCoveragePolicy.evaluate(floorPoints(),cup)
        assertTrue(evidence.diagnostic(),evidence.valid)
        assertEquals(5,evidence.coveredBins)
        assertTrue(evidence.nearBallPoints >= 5)
    }

    @Test fun denseButThirtyFiveCentimeterHighClusterCannotSuppressFull() {
        val cloud = (0..20).flatMap { i ->
            (0..9).map { j ->
                raw(0.05f+i*0.003f,(j-5)*0.009f,0.35f)
            }
        }
        val evidence=PrecisionRawFloorCoveragePolicy.evaluate(cloud,cup)
        assertFalse(evidence.valid)
        assertTrue(evidence.acceptedRawPoints >= 160)
        assertEquals(0,evidence.corridorPoints)
        assertEquals("CORRIDOR_SPARSE",evidence.reason)
    }

    @Test fun denseTinySpotIsNotALineCoverage() {
        val cluster=List(200) { i ->
            raw(0.08f+(i%7)*0.002f,(i%10)*0.008f,0.02f)
        }
        val evidence=PrecisionRawFloorCoveragePolicy.evaluate(cluster,cup)
        assertFalse(evidence.valid)
        assertEquals("INSUFFICIENT_SPATIAL_SPAN",evidence.reason)
    }

    @Test fun noCupMarkerNeverCertifiesRaw() {
        val result=PrecisionRawFloorCoveragePolicy.evaluate(floorPoints(),null)
        assertFalse(result.valid)
        assertEquals("NO_VALID_CUP_MARKER",result.reason)
    }

    @Test fun crowdedHighConfidenceWallOutsidePuttCannotCertifyGround() {
        val points=List(1000) { i ->
            raw((i%19)*0.04f,0.63f,0.01f)
        }
        val result=PrecisionRawFloorCoveragePolicy.evaluate(points,cup)
        assertFalse(result.valid)
        assertEquals(0,result.corridorPoints)
    }

    @Test fun sourceMustBeRawNotFullForCoverageDecision() {
        val full=floorPoints().map {
            PrecisionDepthPoint(it.x,it.y,it.z,it.confidence,it.frameTimestampNs,"full")
        }
        assertFalse(PrecisionRawFloorCoveragePolicy.evaluate(full,cup).valid)
    }
}
