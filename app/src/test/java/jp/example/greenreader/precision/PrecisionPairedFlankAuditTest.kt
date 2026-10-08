package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionPairedFlankAuditTest {
    private val ball = Vec3(0f, 0f, 0f)
    private val cup = Vec3(2f, 0f, 0f)

    private fun synthetic(
        gradeAcross: (Float) -> Float,
        forwardSlope: Float = 0.03f,
        oneSideOnly: Boolean = false,
        staggered: Boolean = false
    ): List<PrecisionSurfaceCell> {
        val out = mutableListOf<PrecisionSurfaceCell>()
        // +X is forward and +Z is the +right analyzer axis.
        for (xi in 0..40) {
            val along = xi * 0.05f
            for (zi in -10..10) {
                if (oneSideOnly && zi > 0) continue
                if (staggered && ((zi < 0 && xi % 5 != 0) ||
                    (zi > 0 && xi % 5 != 3))) continue
                val z = zi * 0.05f
                val height = forwardSlope * along + gradeAcross(along) * z
                out += PrecisionSurfaceCell(along, z, height, 0.95f, 8, 0.001f)
            }
        }
        return out
    }

    @Test fun agreesWithRealRightUphillSurface() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ 0.03f }), ball, cup, 3.0f
        )
        assertEquals(verdict.diagnostic, "PAIRED_HEIGHTS_AGREE", verdict.reason)
        assertTrue(verdict.verifiedAgreement)
        assertFalse(verdict.blocksDirection)
        assertEquals(3.0f, verdict.medianPairedCrossPercent!!, 0.3f)
    }

    @Test fun vetoesReverseSurfaceDespiteCoherentWrongSignFit() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ -0.03f }), ball, cup, 2.5f
        )
        assertEquals(verdict.diagnostic, "OPPOSITE_PAIRED_HEIGHTS", verdict.reason)
        assertTrue(verdict.blocksDirection)
        assertTrue(verdict.opposingSlices >= 6)
    }

    @Test fun oppositeDirectionInputProducesSymmetricResult() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ 0.03f }), ball, cup, -2.5f
        )
        assertTrue(verdict.blocksDirection)
        assertEquals("OPPOSITE_PAIRED_HEIGHTS", verdict.reason)
    }

    @Test fun oneSideCoverageRemainsUnverifiedRatherThanAnError() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ -0.04f }, oneSideOnly = true), ball, cup, 4f
        )
        assertEquals("INSUFFICIENT_PAIRED_COVERAGE", verdict.reason)
        assertFalse(verdict.blocksDirection)
        assertFalse(verdict.verifiedAgreement)
    }

    @Test fun complexGreenIsNotForcedIntoOneSide() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ along -> if (along < 1f) -0.03f else 0.03f }),
            ball, cup, 2.5f
        )
        assertFalse(verdict.blocksDirection)
        assertFalse(verdict.verifiedAgreement)
    }

    @Test fun nearFlatDoesNotInventADirection() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ 0.002f }), ball, cup, 0.2f
        )
        assertEquals("NO_DIRECTION_TO_AUDIT", verdict.reason)
        assertFalse(verdict.blocksDirection)
    }

    @Test fun unequalSamplingInForwardDirectionDoesNotFakeACrossSlope() {
        val verdict = PrecisionPairedFlankAudit.evaluate(
            synthetic({ 0f }, forwardSlope = .10f, staggered = true),
            ball, cup, 2.3f
        )
        assertFalse(verdict.blocksDirection)
        assertFalse(verdict.verifiedAgreement)
    }
}
