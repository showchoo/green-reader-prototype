package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionDepthProvenanceTest {
    @Test fun untaggedLegacyPointsRemainCompatible() {
        val p = PrecisionDepthPoint(1f, 2f, 3f, 0.5f, 123456L)
        assertEquals("unknown", p.depthSource)
        assertEquals(123456L, p.frameTimestampNs)
    }

    @Test fun rawAndFullPointsRetainSource() {
        val raw = PrecisionDepthPoint(1f, 0f, 2f, 0.9f, 123L, "raw")
        val full = PrecisionDepthPoint(1f, 0f, 2f, 0.65f, 123L, "full")
        assertEquals("raw", raw.depthSource)
        assertEquals("full", full.depthSource)
    }
}
