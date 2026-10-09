package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.abs

class PrecisionAnchoredGroundSelectorTest {
    private val ball = Vec3(0f, 0f, 0f)
    private fun grid(
        offset: Float, xStart: Int, xEnd: Int,
        zStart: Int, zEnd: Int, step: Float = .05f,
        slope: Float = 0f
    ): List<PrecisionAnchoredGroundSelector.Observation> =
        (xStart..xEnd).flatMap { i ->
            (zStart..zEnd).map { j ->
                val x = i * step
                val z = j * step
                PrecisionAnchoredGroundSelector.Observation(x,z,offset+slope*z)
            }
        }

    @Test fun floorWinsEvenWhenFurnitureHasMoreCells() {
        val floor = grid(.028f,-5,5,-15,5,slope=.03f)
        val furniture = grid(.82f,9,18,-20,6)
        val result = PrecisionAnchoredGroundSelector.select(floor+furniture,ball)
        assertTrue(result.diagnostic(),result.valid)
        assertEquals(PrecisionAnchoredGroundSelector.Status.ANCHORED,result.status)
        assertTrue(abs(result.referenceHeight!!-.025f)<.04f)
        assertTrue(result.seedIndices.all { it < floor.size })
    }

    @Test fun distantButVerySmoothTableIsNotTheFloor() {
        val table = grid(.78f,-6,15,-24,10)
        val result=PrecisionAnchoredGroundSelector.select(table,ball)
        assertEquals(
            PrecisionAnchoredGroundSelector.Status.NO_NEAR_BALL_GROUND,
            result.status
        )
        assertFalse(result.valid)
        assertNull(result.referenceHeight)
    }

    @Test fun sparseNearBallCannotFakeGroundSupport() {
        val sparse = grid(.08f,-1,1,-1,1)
        val table = grid(1.20f,8,20,-20,10)
        val v=PrecisionAnchoredGroundSelector.select(sparse+table,ball)
        assertEquals(PrecisionAnchoredGroundSelector.Status.NO_NEAR_BALL_GROUND,v.status)
        assertFalse(v.valid)
    }

    @Test fun genuineSlopedGreenIsNotForcedHorizontal() {
        val floor = grid(-.04f,-7,7,-19,4,slope=.07f)
        val v=PrecisionAnchoredGroundSelector.select(floor,ball)
        assertTrue(v.diagnostic(),v.valid)
        assertTrue(v.referenceHeight!!<0f)
    }

    @Test fun ballOffsetOtherThanWorldOriginUsesRealMarker() {
        val otherBall=Vec3(1.05f,.15f,-1.5f)
        val floor=grid(.15f,17,24,-35,-25)
        val v=PrecisionAnchoredGroundSelector.select(floor,otherBall)
        assertTrue(v.diagnostic(),v.valid)
        assertTrue(abs(v.referenceHeight!!-.15f)<.02f)
    }

    @Test fun acceptedSceneIsNotCalibratedToBallHeight() {
        val floor=grid(.095f,-6,6,-15,4)
        val v=PrecisionAnchoredGroundSelector.select(floor,ball)
        assertTrue(v.valid)
        assertTrue(v.referenceHeight!!>.085f)
    }

    @Test fun severeMarkerHeightMismatchFailsClosed() {
        val floor=grid(-.47f,-7,7,-18,6)
        val v=PrecisionAnchoredGroundSelector.select(floor,ball)
        assertFalse(v.valid)
        assertEquals(PrecisionAnchoredGroundSelector.Status.NO_NEAR_BALL_GROUND,v.status)
    }

    @Test fun integratedSurfaceCannotSeedDistantTable() {
        val p=ArrayList<PrecisionDepthPoint>()
        var frame=1L
        for (i in -7..7) for (j in -18..5) {
            val x=i*.05f
            val z=j*.05f
            repeat(5) { tick ->
                p+=PrecisionDepthPoint(x,.03f+.025f*z+(tick-2)*.001f,z,.9f,tick.toLong()+1)
            }
        }
        // In aggregate, an extensive furniture plane would previously
        // dominate the global 5cm height-bin count.
        for (i in 7..18) for (j in -19..5) {
            val x=i*.05f
            val z=j*.05f
            repeat(5) { tick ->
                p+=PrecisionDepthPoint(x,.82f+(tick-2)*.001f,z,.9f,tick.toLong()+1)
            }
        }
        val surface=PrecisionSurfaceBuilder.build(
            p,ball,Vec3(0f,-.02f,-.8f)
        )
        assertTrue(PrecisionSurfaceBuilder.lastDiagnostic,surface.groundCellCount>=25)
        assertTrue(surface.cells.all { abs(it.height)<.20f })
        assertTrue(PrecisionSurfaceBuilder.lastDiagnostic.contains("ANCHORED_GROUND status=ANCHORED"))
    }

    @Test fun integratedNoNearbyGroundLeavesNoFalseOutput() {
        val p=ArrayList<PrecisionDepthPoint>()
        for (i in -8..8) for (j in -15..10) {
            val x=i*.05f
            val z=j*.05f
            repeat(4) { tick ->
                p+=PrecisionDepthPoint(x,.85f+tick*.0001f,z,.96f,tick.toLong()+1)
            }
        }
        val surface=PrecisionSurfaceBuilder.build(p,ball,Vec3(0f,0f,-.8f))
        assertEquals(0,surface.groundCellCount)
        assertTrue(PrecisionSurfaceBuilder.lastDiagnostic.contains("NO_NEAR_BALL_GROUND"))
    }
}
