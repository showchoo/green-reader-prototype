package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionFullDepthSupplementPolicyTest {
    @Test fun shortScanKeepsRawOnlyWhenRawSucceeded() {
        val plan = PrecisionFullDepthSupplementPolicy.plan(
            rawAccepted = true,
            requestedMinDepthM = 0.25f,
            requestedMaxDepthM = 5.0f,
            ballAxialDepthM = 2.8f
        )
        assertFalse(plan.useFull)
    }

    @Test fun longScanSupplementsFromJustBeforeBallDepth() {
        val plan = PrecisionFullDepthSupplementPolicy.plan(
            rawAccepted = true,
            requestedMinDepthM = 0.25f,
            requestedMaxDepthM = 6.97f,
            ballAxialDepthM = 2.96f
        )
        assertTrue(plan.useFull)
        assertEquals(2.46f, plan.minDepthM, 0.001f)
    }

    @Test fun noRawFallsBackToFullAcrossWholeRequestedRange() {
        val plan = PrecisionFullDepthSupplementPolicy.plan(
            rawAccepted = false,
            requestedMinDepthM = 0.25f,
            requestedMaxDepthM = 6.97f,
            ballAxialDepthM = 2.96f
        )
        assertTrue(plan.useFull)
        assertEquals(0.25f, plan.minDepthM, 0.001f)
    }
}
