package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionDepthSourceAuditTest {
    @Test fun independentSourcesAgreeOnRightDownhill() {
        val v = PrecisionDepthSourceAudit.judge(
            -2.5f, -2.4f, -2.6f, 6000, 7000, 12, 14
        )
        assertEquals("RAW_FULL_AGREE", v.reason)
        assertTrue(v.crossSourceVerified)
        assertFalse(v.blocksDirection)
    }

    @Test fun oppositeRawAndFullDirectionsBlockFalseHookSlice() {
        val v = PrecisionDepthSourceAudit.judge(
            2.0f, -2.4f, 2.5f, 6000, 7000, 12, 14
        )
        assertEquals("OPPOSITE_RAW_FULL", v.reason)
        assertTrue(v.blocksDirection)
    }

    @Test fun largeSameSignDifferenceStillBlocksUnreliableDirection() {
        val v = PrecisionDepthSourceAudit.judge(
            3f, 1.4f, 6f, 6000, 7000, 8, 10
        )
        assertEquals("RAW_FULL_MAGNITUDE_DISAGREEMENT", v.reason)
        assertTrue(v.blocksDirection)
    }

    @Test fun weakFullSlopeIsNotConfirmation() {
        val v = PrecisionDepthSourceAudit.judge(
            -2f, -2.3f, -0.1f, 6000, 7000, 8, 10
        )
        assertEquals("WEAK_SOURCE_DIRECTION", v.reason)
        assertTrue(v.blocksDirection)
    }

    @Test fun oneDepthTypeMeansUnverifiedNotFalseAgreement() {
        val rawOnly = PrecisionDepthSourceAudit.judge(
            -2f, -2f, null, 10000, 0, 20, 0
        )
        assertFalse(rawOnly.blocksDirection)
        assertFalse(rawOnly.crossSourceVerified)
        assertEquals("INSUFFICIENT_DUAL_SOURCE", rawOnly.reason)
    }

    @Test fun sourcesAgainstMainDirectionGetVeto() {
        val v = PrecisionDepthSourceAudit.judge(
            2f, -2.3f, -2.5f, 5000, 5000, 8, 8
        )
        assertEquals("SOURCES_OPPOSE_AGGREGATE", v.reason)
        assertTrue(v.blocksDirection)
    }

    @Test fun missingFitWhenBothDataRichMustNotPass() {
        val v = PrecisionDepthSourceAudit.judge(
            2f, null, 2.2f, 5000, 5000, 8, 8
        )
        assertEquals("SOURCE_FIT_UNRESOLVED", v.reason)
        assertTrue(v.blocksDirection)
    }

    private fun points(rawSlope: Float, fullSlope: Float): List<PrecisionDepthPoint> {
        val result = ArrayList<PrecisionDepthPoint>()
        for (source in listOf("raw", "full")) {
            val slope = if (source == "raw") rawSlope else fullSlope
            for (frame in 1..7) {
                for (xi in -3..32) {
                    for (zi in -9..9) {
                        val x = xi * .065f
                        val z = zi * .065f
                        result += PrecisionDepthPoint(
                            x = x,
                            y = slope * z + ((frame + xi * 7 + zi * 13) % 5) * 0.0001f,
                            z = z,
                            confidence = .92f,
                            frameTimestampNs = frame.toLong(),
                            depthSource = source
                        )
                    }
                }
            }
        }
        return result
    }

    @Test fun reconstructedSyntheticSlopesDetectOppositeSources() {
        val points = points(-.028f, .030f)
        val result = PrecisionDepthSourceAudit.analyze(
            points, Vec3(0f,0f,0f), Vec3(2f,0f,0f), 2f
        )
        assertEquals(result.diagnostic, "OPPOSITE_RAW_FULL", result.reason)
        assertTrue(result.blocksDirection)
        assertNotNull(result.raw.crossPercent)
        assertNotNull(result.full.crossPercent)
    }

    @Test fun reconstructedSyntheticSlopesRetainAgreedDirection() {
        val points = points(-.028f, -.031f)
        val result = PrecisionDepthSourceAudit.analyze(
            points, Vec3(0f,0f,0f), Vec3(2f,0f,0f), -2.8f
        )
        assertEquals(result.diagnostic, "RAW_FULL_AGREE", result.reason)
        assertFalse(result.blocksDirection)
        assertTrue(result.crossSourceVerified)
    }
}
