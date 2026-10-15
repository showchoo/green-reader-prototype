package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionMarkerFloorOffsetAuditTest {
    private fun floor(base: Float, longitudinal: Float,
                      withCup: Boolean = true): PrecisionSurfaceModel {
        val cells=ArrayList<PrecisionSurfaceCell>()
        for (i in 0..20) for (j in -5..5) {
            if (!withCup && i > 5) continue
            val z=-i*0.04f
            val x=j*0.03f
            val y=base+longitudinal*(-z)
            cells += PrecisionSurfaceCell(x,z,y,0.95f,6,.002f)
        }
        return PrecisionSurfaceModel(cells,.04f,10000,8,groundCellCount=cells.size)
    }
    private val ball=Vec3(0f,0f,0f)
    private val cup=Vec3(0f,0f,-0.80f)

    @Test fun equalMarkerVerticalBiasIsVisibleEvenIfDeltaCancels() {
        val r=PrecisionMarkerFloorOffsetAudit.evaluate(floor(.32f,0f),ball,cup)
        assertTrue(r.ballCells>=6)
        assertTrue(r.cupCells>=6)
        assertEquals(-32f,r.ballMarkerMinusDepthCm!!,0.2f)
        assertEquals(-32f,r.cupMarkerMinusDepthCm!!,0.2f)
        assertTrue(r.diagnostic().contains("groundTruth=false"))
    }

    @Test fun missingCupDoesNotInventHeightOffset() {
        val r=PrecisionMarkerFloorOffsetAudit.evaluate(
            floor(.02f,0f,withCup=false),ball,cup)
        assertTrue(r.ballDepthHeightM != null)
        assertTrue(r.cupDepthHeightM == null)
        assertTrue(r.diagnostic().contains("cupMarkerMinusDepthCm=NA"))
    }

    @Test fun sourceGroundOffsetAtCupIsSeparateFromBallOffset() {
        val r=PrecisionMarkerFloorOffsetAudit.evaluate(
            floor(.01f,.06f),ball,cup)
        assertTrue(kotlin.math.abs(
            r.ballMarkerMinusDepthCm!!-r.cupMarkerMinusDepthCm!!) > 3f)
    }
}
