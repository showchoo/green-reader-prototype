package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionMatchedCellFlanksTest {
    private val ball = Vec3(0f, 0f, 0f)
    private val cup = Vec3(2f, 0f, 0f)

    private fun biasedCoverage(crossGrade: Float, uneven: Boolean = true): List<PrecisionSurfaceCell> {
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (slice in 0 until 8) {
            val x = slice * 0.25f + 0.05f
            for (i in 0 until 6) {
                val forward = x + i * 0.001f
                val leftZ = -0.15f - (i % 2) * 0.01f
                val rightZ = 0.15f + (i % 2) * 0.01f
                cells += cell(forward, leftZ, crossGrade)
                cells += cell(forward, rightZ, crossGrade)
            }
            if (uneven) {
                // Additional right-side data makes the right median forward
                // position 9cm later than the left median, even though six
                // legitimate forward-matched pairs exist in every slice.
                for (i in 0 until 9) {
                    cells += cell(x + 0.09f + i * 0.001f, 0.17f, crossGrade)
                }
            }
        }
        return cells
    }

    private fun cell(x: Float, z: Float, grade: Float): PrecisionSurfaceCell =
        PrecisionSurfaceCell(x, z, x * 0.12f + z * grade, 0.92f, 8, 0.001f)

    @Test fun unevenForwardCoverageDoesNotHideRealAgreement() {
        val v = PrecisionPairedFlankAudit.evaluate(biasedCoverage(+.030f), ball, cup, +3f)
        assertEquals(v.diagnostic, "PAIRED_HEIGHTS_AGREE", v.reason)
        assertFalse(v.blocksDirection)
        assertTrue(v.verifiedAgreement)
        assertEquals(8, v.validSlices)
        assertTrue(v.matchedCellPairs >= 48)
        assertEquals(0, v.forwardMismatchSlices)
        assertTrue(v.diagnostic.contains("matchedPairs="))
    }

    @Test fun sameMatchedEvidenceCanVetoOppositeClaim() {
        val v = PrecisionPairedFlankAudit.evaluate(biasedCoverage(+.030f), ball, cup, -2f)
        assertEquals(v.diagnostic, "OPPOSITE_PAIRED_HEIGHTS", v.reason)
        assertTrue(v.blocksDirection)
        assertTrue(v.matchedCellPairs >= 48)
    }

    @Test fun oneAccidentalPairPerSliceMustNotCountAsEvidence() {
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (slice in 0 until 8) {
            val x = slice * 0.25f + 0.05f
            for (i in 0 until 6) {
                cells += cell(x + i * 0.001f, -0.15f, +.030f)
            }
            cells += cell(x + 0.001f, +0.15f, +.030f)
            for (i in 0 until 6) {
                cells += cell(x + 0.08f + i * 0.001f, +0.15f, +.030f)
            }
        }
        val v = PrecisionPairedFlankAudit.evaluate(cells, ball, cup, -2f)
        assertEquals("INSUFFICIENT_PAIRED_COVERAGE", v.reason)
        assertFalse(v.blocksDirection)
        assertFalse(v.verifiedAgreement)
        assertEquals(0, v.validSlices)
        assertEquals(0, v.matchedCellPairs)
        assertTrue(v.forwardMismatchSlices >= 6)
    }

    @Test fun mixedContourMustRemainInconclusive() {
        val cells = ArrayList<PrecisionSurfaceCell>()
        for (slice in 0 until 8) {
            val x = slice * 0.25f + 0.05f
            val cross = if (slice % 2 == 0) +.030f else -.030f
            for (i in 0 until 6) {
                val f = x + i * 0.001f
                cells += cell(f, -.16f, cross)
                cells += cell(f, +.16f, cross)
            }
        }
        val v = PrecisionPairedFlankAudit.evaluate(cells, ball, cup, +2f)
        assertEquals(v.diagnostic, "MIXED_OR_WEAK_PAIRED_HEIGHTS", v.reason)
        assertFalse(v.blocksDirection)
        assertFalse(v.verifiedAgreement)
        assertEquals(8, v.validSlices)
    }
}
