package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionForwardMatchingTest {
    private val ball = Vec3(0f, 0f, 0f)
    private val cup = Vec3(2f, 0f, 0f)

    private fun artificialFlanks(
        rightForwardShiftM: Float,
        crossGrade: Float,
        forwardGrade: Float
    ): List<PrecisionSurfaceCell> {
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (segment in 0 until 8) {
            val start = segment * 0.25f + 0.055f
            for (i in 0 until 6) {
                val sharedJitter = (i % 3) * 0.001f
                val leftX = start + sharedJitter
                val rightX = start + rightForwardShiftM + sharedJitter
                val leftZ = -0.15f - (i % 2) * 0.01f
                val rightZ = 0.15f + (i % 2) * 0.01f
                cells += PrecisionSurfaceCell(
                    leftX, leftZ, leftX * forwardGrade + leftZ * crossGrade,
                    0.92f, 8, 0.001f
                )
                cells += PrecisionSurfaceCell(
                    rightX, rightZ, rightX * forwardGrade + rightZ * crossGrade,
                    0.92f, 8, 0.001f
                )
            }
        }
        return cells
    }

    @Test fun longitudinalSlopeMustNotCreateFalseReverseCrossVeto() {
        // 12% longitudinal grade + 4cm forward mismatch makes a spurious
        // ~+1.5% apparent cross grade on physically cross-flat turf.
        // v8.1's 5cm tolerance could incorrectly veto a -2% report.
        val v = PrecisionPairedFlankAudit.evaluate(
            artificialFlanks(.04f, 0f, .12f), ball, cup, -2f
        )
        assertEquals("INSUFFICIENT_PAIRED_COVERAGE", v.reason)
        assertFalse(v.blocksDirection)
        assertFalse(v.verifiedAgreement)
        assertTrue("forward mismatch must be diagnosed", v.forwardMismatchSlices >= 6)
    }

    @Test fun realOppositeCrossRemainsDetectableWhenForwardMatches() {
        val v = PrecisionPairedFlankAudit.evaluate(
            artificialFlanks(0f, +.030f, .12f), ball, cup, -2f
        )
        assertEquals(v.diagnostic, "OPPOSITE_PAIRED_HEIGHTS", v.reason)
        assertTrue(v.blocksDirection)
        assertEquals(0, v.forwardMismatchSlices)
        assertTrue(v.validSlices >= 6)
    }

    @Test fun matchingPositiveSlopeRemainsUsable() {
        val v = PrecisionPairedFlankAudit.evaluate(
            artificialFlanks(0f, +.030f, .12f), ball, cup, +3f
        )
        assertEquals(v.diagnostic, "PAIRED_HEIGHTS_AGREE", v.reason)
        assertFalse(v.blocksDirection)
        assertTrue(v.verifiedAgreement)
    }

    @Test fun moderateMismatchCanBeInconclusiveWithoutClaimingAccuracy() {
        val v = PrecisionPairedFlankAudit.evaluate(
            artificialFlanks(.020f, -.030f, 0f), ball, cup, +3f
        )
        assertFalse(v.blocksDirection)
        assertFalse(v.verifiedAgreement)
        assertTrue(v.diagnostic.contains("forwardMismatch="))
    }
}
