package jp.example.greenreader.analysis

import org.junit.Assert.assertEquals
import org.junit.Test

class DisplayDirectionCalibrationTest {
    @Test
    fun finalFieldCalibrationFlipsGeometricScreenConvention() {
        assertEquals(
            -2.5f,
            DisplayDirectionCalibration.renderCrossPercent(2.5f, 1f),
            0.0001f
        )
        assertEquals(
            2.5f,
            DisplayDirectionCalibration.renderCrossPercent(2.5f, -1f),
            0.0001f
        )
    }

    @Test
    fun aimAndSlopeUseTheSameFinalScreenConvention() {
        assertEquals(
            -14f,
            DisplayDirectionCalibration.renderAimOffsetCm(14f, 1f),
            0.0001f
        )
        assertEquals(
            14f,
            DisplayDirectionCalibration.renderAimOffsetCm(14f, -1f),
            0.0001f
        )
    }
}
