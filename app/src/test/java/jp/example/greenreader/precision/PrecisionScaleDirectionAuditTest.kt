package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionScaleDirectionAuditTest {
    @Test fun oppositeRadius50BlocksCurve() {
        val v = PrecisionScaleDirectionAudit.compare(-2.57f, 1.84f, 2.68f)
        assertEquals("RADIUS50_OPPOSITE", v.reason)
        assertTrue(v.blocksDirection)
        assertFalse(v.allScalesAgree)
    }

    @Test fun oppositeRadius80BlocksEvenIfRadius50Agrees() {
        val v = PrecisionScaleDirectionAudit.compare(3.78f, 2.1f, -1.1f)
        assertEquals("RADIUS80_OPPOSITE", v.reason)
        assertTrue(v.blocksDirection)
    }

    @Test fun consistentScalesRemainAllowed() {
        val v = PrecisionScaleDirectionAudit.compare(-2.0f, -1.7f, -2.6f)
        assertEquals("SCALES_AGREE", v.reason)
        assertFalse(v.blocksDirection)
        assertTrue(v.allScalesAgree)
    }

    @Test fun missingOrWeakScaleIsInconclusiveNotProofOfAccuracy() {
        val v = PrecisionScaleDirectionAudit.compare(-3f, null, -0.2f)
        assertEquals("SCALE_EVIDENCE_INCOMPLETE", v.reason)
        assertFalse(v.blocksDirection)
        assertFalse(v.allScalesAgree)
        assertFalse(PrecisionScaleDirectionAudit.compare(.2f, -3f, 4f).blocksDirection)
    }

    @Test fun syntheticStraightSlopeAgreesAtAllThreeRadii() {
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (xi in -4..44) {
            for (zi in -16..16) {
                val x = xi * 0.05f
                val z = zi * 0.05f
                cells += PrecisionSurfaceCell(
                    x, z, -0.03f * z + 0.01f * x,
                    .95f, 12, 0.001f
                )
            }
        }
        val s = PrecisionSurfaceModel(
            cells = cells,
            voxelSizeMeters = .05f,
            sourcePointCount = 40000,
            uniqueFrames = 20
        )
        val ball = Vec3(0f,0f,0f)
        val cup = Vec3(2f,.02f,0f)
        val core = PrecisionSlopeAnalyzer.analyze(s, ball, cup)!!
        assertEquals(-3f, core.overallCrossPercent, 0.5f)
        val v = PrecisionScaleDirectionAudit.evaluate(
            s,ball,cup,core.overallCrossPercent
        )
        assertEquals(v.diagnostic, "SCALES_AGREE", v.reason)
        assertFalse(v.blocksDirection)
        assertEquals(-3f,v.radius50Cross!!,0.5f)
        assertEquals(-3f,v.radius80Cross!!,0.5f)
    }

    @Test fun shallowFlatGreenCannotClaimVerifiedDirection() {
        val v = PrecisionScaleDirectionAudit.compare(0f, 0f, 0f)
        assertEquals("UNRESOLVED_BASELINE", v.reason)
        assertFalse(v.allScalesAgree)
    }
}
