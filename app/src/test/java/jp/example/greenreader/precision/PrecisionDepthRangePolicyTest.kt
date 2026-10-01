package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionDepthRangePolicyTest {
    @Test fun shortScanKeepsFiveMeterFloor() {
        val camera = Vec3(0f, 0f, 0f)
        val ball = Vec3(0f, -1f, -2f)
        val cup = Vec3(0f, -1f, -3f)
        assertEquals(5.0f, PrecisionDepthRangePolicy.maxDepthM(camera, ball, cup), 0.0001f)
    }

    @Test fun loggedLongPuttExtendsPastCupInsteadOfClippingAtFiveMeters() {
        val camera = Vec3(0.056355413f, 0.004358414f, 0.0077345436f)
        val ball = Vec3(-0.012305353f, -1.2264777f, -2.6813304f)
        val cup = Vec3(0.050335106f, -1.0163503f, -5.6413f)
        val maxDepth = PrecisionDepthRangePolicy.maxDepthM(camera, ball, cup)
        assertEquals(6.49f, maxDepth, 0.05f)
    }

    @Test fun pathologicalDistanceIsCappedAtTwelveMeters() {
        val camera = Vec3(0f, 0f, 0f)
        val ball = Vec3(0f, 0f, -2f)
        val cup = Vec3(0f, 0f, -20f)
        assertEquals(12.0f, PrecisionDepthRangePolicy.maxDepthM(camera, ball, cup), 0.0001f)
    }
}
