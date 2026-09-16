package jp.example.greenreader.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FieldOrientationCalibrationTest {
    @Test
    fun flipsOnlyCrossSlopeSign() {
        val report = SlopeReport(
            distanceMeters = 2.4f,
            segments = listOf(
                SlopeSegment(0f, 1.2f, 1.5f, 2.2f, 0.01f, 120),
                SlopeSegment(1.2f, 2.4f, -0.8f, -1.7f, 0.02f, 110)
            ),
            overallLongitudinalPercent = 0.4f,
            overallCrossPercent = 1.9f,
            pointCount = 230
        )

        val corrected = FieldOrientationCalibration.correctCrossSign(report)

        assertEquals(-1.9f, corrected.overallCrossPercent, 0.0001f)
        assertEquals(-2.2f, corrected.segments[0].crossPercent, 0.0001f)
        assertEquals(1.7f, corrected.segments[1].crossPercent, 0.0001f)
        assertEquals(0.4f, corrected.overallLongitudinalPercent, 0.0001f)
        assertEquals(2.4f, corrected.distanceMeters, 0.0001f)
        assertTrue(corrected.pointCount == 230)
    }
}
