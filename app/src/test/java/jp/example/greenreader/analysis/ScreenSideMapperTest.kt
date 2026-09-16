package jp.example.greenreader.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ScreenSideMapperTest {
    @Test
    fun upwardPuttTreatsScreenRightAsPositive() {
        // Ball -> cup is straight up on screen: u=(0,-1), so screen-right=(+1,0).
        assertEquals(
            1f,
            ScreenSideMapper.projectedCrossToScreenRightSign(0f, -1f, 1f, 0f)!!,
            0.0001f
        )
        assertEquals(
            -1f,
            ScreenSideMapper.projectedCrossToScreenRightSign(0f, -1f, -1f, 0f)!!,
            0.0001f
        )
    }

    @Test
    fun rotatedPuttUsesRightNormalOfTheLine() {
        // For u=(1,0) (putt goes right), screen-right normal is (0,+1).
        assertEquals(
            1f,
            ScreenSideMapper.projectedCrossToScreenRightSign(1f, 0f, 0f, 1f)!!,
            0.0001f
        )
        assertEquals(
            -1f,
            ScreenSideMapper.projectedCrossToScreenRightSign(1f, 0f, 0f, -1f)!!,
            0.0001f
        )
    }

    @Test
    fun nearlyParallelProjectionIsRejected() {
        assertNull(ScreenSideMapper.projectedCrossToScreenRightSign(0f, -1f, 0.01f, 1f))
    }
}
