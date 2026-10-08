package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionTemporalConsistencyTest {
    @Test fun stableFiveWindowsPass() {
        val result = PrecisionTemporalConsistency.evaluate(
            listOf(
                Pair(1.0f, -0.2f),
                Pair(1.1f, -0.2f),
                Pair(1.1f, -0.3f),
                Pair(1.2f, -0.3f),
                Pair(1.0f, -0.4f)
            )
        )
        assertTrue(result.verified)
        assertFalse(result.unstable)
        assertEquals(5, result.validWindows)
        assertTrue(result.disagreementPp < 0.3f)
    }

    @Test fun largeTemporalDriftIsRejected() {
        val result = PrecisionTemporalConsistency.evaluate(
            listOf(
                Pair(0.0f, 0.0f),
                Pair(0.1f, 0.0f),
                Pair(4.0f, 0.0f),
                Pair(4.1f, 0.0f),
                Pair(4.2f, 0.0f)
            )
        )
        assertTrue(result.verified)
        assertTrue(result.unstable)
        assertTrue(result.disagreementPp > 2.5f)
        assertTrue(result.diagnostic.contains("UNSTABLE"))
    }

    @Test fun insufficientWindowsAreNotFalselyCalledStable() {
        val result = PrecisionTemporalConsistency.evaluate(
            listOf(Pair(0.0f, 0.0f), null, Pair(5.0f, 0.0f))
        )
        assertFalse(result.verified)
        assertFalse(result.unstable)
        assertTrue(result.disagreementPp.isNaN())
        assertEquals(2, result.validWindows)
    }

    @Test fun nonfiniteWindowExcluded() {
        val result = PrecisionTemporalConsistency.evaluate(
            listOf(
                Pair(Float.NaN, 0f),
                Pair(1f, 1f),
                Pair(1.1f, 1f),
                Pair(1f, 1.1f),
                Pair(1f, 1f)
            )
        )
        assertTrue(result.verified)
        assertFalse(result.unstable)
        assertEquals(4, result.validWindows)
    }

    @Test fun thresholdStrictlyGreater() {
        val result = PrecisionTemporalConsistency.evaluate(
            listOf(
                Pair(0f, 0f), Pair(0f, 0f),
                Pair(2.5f, 0f), Pair(2.5f, 0f)
            )
        )
        assertFalse(result.unstable)
        assertEquals(2.5f, result.disagreementPp, 0.001f)
    }
}
