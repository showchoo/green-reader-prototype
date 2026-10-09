package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionMarkerDepthHeightAuditTest {
    private fun model(slope: Float, base: Float = .12f, cover: Boolean = true):
        PrecisionSurfaceModel {
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (i in 0..16) for (j in -4..4) {
            val x = j * .03f
            val z = -(i * .04f)
            if (!cover && i > 3) continue
            val along = -z
            cells.add(PrecisionSurfaceCell(x, z, base+slope*along, 1f, 6, .001f))
        }
        return PrecisionSurfaceModel(cells, .03f, 10000, 8,
            groundCellCount=cells.size)
    }
    private val ball = Vec3(0f, 0f, 0f)

    @Test fun realSlopeSameOnBothChannelsPassesEvenIfSteep() {
        val cup = Vec3(0f, .034f, -.68f)
        val v = PrecisionMarkerDepthHeightAudit.evaluate(model(.05f), ball, cup)
        assertEquals(PrecisionMarkerDepthHeightAudit.Status.CONSISTENT, v.status)
        assertTrue(v.trustForQuality)
        assertFalse(v.independentGroundTruth)
    }
    @Test fun oppositeMarkerAndDepthSlopeMustWarn() {
        val cup = Vec3(0f, -.03865f, -.68f)
        val v = PrecisionMarkerDepthHeightAudit.evaluate(model(.046f), ball, cup)
        assertEquals(PrecisionMarkerDepthHeightAudit.Status.DISAGREEMENT, v.status)
        assertTrue(v.discrepancyMeters!! > .06f)
        assertFalse(v.trustForQuality)
        assertTrue(v.summary().contains("independentGroundTruth=false"))
    }
    @Test fun missingCupCoverageIsInconclusiveNotZero() {
        val v = PrecisionMarkerDepthHeightAudit.evaluate(model(.046f, cover=false),
            ball, Vec3(0f,-.038f,-.68f))
        assertEquals(PrecisionMarkerDepthHeightAudit.Status.INSUFFICIENT_COVERAGE,v.status)
        assertNull(v.depthDeltaMeters)
        assertNull(v.discrepancyMeters)
    }
    @Test fun constantVerticalOffsetDoesNotCreateFalseMismatch() {
        val cup = Vec3(0f, .023f, -.68f)
        val a = PrecisionMarkerDepthHeightAudit.evaluate(model(.035f,base=0f),ball,cup)
        val b = PrecisionMarkerDepthHeightAudit.evaluate(model(.035f,base=.60f),ball,cup)
        assertEquals(a.status,b.status)
        assertEquals(a.depthDeltaMeters!!,b.depthDeltaMeters!!,.00001f)
    }
    @Test fun noPointsFailsClosed() {
        val empty = PrecisionSurfaceModel(emptyList(),.05f,0,0)
        val v = PrecisionMarkerDepthHeightAudit.evaluate(empty,ball,Vec3(0f,0f,-.68f))
        assertEquals(PrecisionMarkerDepthHeightAudit.Status.INSUFFICIENT_COVERAGE,v.status)
        assertNull(v.depthDeltaMeters)
    }
}
