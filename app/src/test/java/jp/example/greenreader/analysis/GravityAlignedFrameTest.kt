package jp.example.greenreader.analysis

import org.junit.Assert.assertEquals
import org.junit.Test

class GravityAlignedFrameTest {
    @Test
    fun preservesWorldVerticalOnFlatFloor() {
        val frame = GravityAlignedFrame.fromYawBasis(
            originX = 2f,
            originY = 1.25f,
            originZ = -3f,
            rightX = 0.6f,
            rightZ = 0.8f
        )
        val a = frame.worldToLocal(floatArrayOf(2.0f, 1.25f, -3.0f))
        val b = frame.worldToLocal(floatArrayOf(3.2f, 1.25f, -1.4f))
        assertEquals(0f, a[1], 1e-6f)
        assertEquals(0f, b[1], 1e-6f)
    }

    @Test
    fun roundTripKeepsHeightAndPosition() {
        val frame = GravityAlignedFrame.fromYawBasis(
            originX = -1.2f,
            originY = 0.7f,
            originZ = 4.1f,
            rightX = -0.8f,
            rightZ = 0.6f
        )
        val world = floatArrayOf(0.4f, 0.73f, 5.5f)
        val local = frame.worldToLocal(world)
        val roundTrip = frame.localToWorld(local)
        assertEquals(world[0], roundTrip[0], 1e-5f)
        assertEquals(world[1], roundTrip[1], 1e-5f)
        assertEquals(world[2], roundTrip[2], 1e-5f)
    }

    @Test
    fun slopeHeightDependsOnlyOnWorldY() {
        val frame = GravityAlignedFrame.fromYawBasis(
            originX = 0f,
            originY = 0f,
            originZ = 0f,
            rightX = 0.173648f,
            rightZ = 0.984808f
        )
        val low = frame.worldToLocal(floatArrayOf(0f, 0f, 0f))
        val high = frame.worldToLocal(floatArrayOf(1f, 0.02f, 2f))
        assertEquals(0.02f, high[1] - low[1], 1e-6f)
    }
}
