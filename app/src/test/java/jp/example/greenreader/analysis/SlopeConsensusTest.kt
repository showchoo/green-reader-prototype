package jp.example.greenreader.analysis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SlopeConsensusTest {
    private fun report(cross: Float, longitudinal: Float = 1f): SlopeReport {
        val segments = (0 until 8).map { i ->
            SlopeSegment(
                startMeters = i * 0.25f,
                endMeters = (i + 1) * 0.25f,
                longitudinalPercent = longitudinal,
                crossPercent = cross,
                elevationMeters = i * 0.002f,
                sampleCount = 120
            )
        }
        return SlopeReport(
            distanceMeters = 2f,
            segments = segments,
            overallLongitudinalPercent = longitudinal,
            overallCrossPercent = cross,
            pointCount = 960
        )
    }

    @Test
    fun threeMatchingRightDownScansBeatTwoReversedOutliers() {
        val consensus = SlopeConsensus.combine(
            listOf(
                report(-2.8f),
                report(-3.1f),
                report(2.6f),
                report(-2.9f),
                report(3.0f)
            )
        )

        assertTrue(consensus != null)
        assertTrue(consensus!!.overallCrossPercent < 0f)
        assertTrue(consensus.segments.all { it.crossPercent < 0f })
        assertEquals(-2.9f, consensus.overallCrossPercent, 0.001f)
    }

    @Test
    fun medianRejectsOneExtremeMagnitude() {
        val consensus = SlopeConsensus.combine(
            listOf(
                report(-2.0f, 1.0f),
                report(-2.2f, 1.1f),
                report(-25f, 8f),
                report(-2.1f, 0.9f),
                report(2.4f, 1.2f)
            )
        )

        assertTrue(consensus != null)
        assertTrue(consensus!!.overallCrossPercent in -2.3f..-1.9f)
        assertTrue(consensus.overallLongitudinalPercent in 0.9f..1.2f)
    }

    @Test
    fun noThreeWayDirectionAgreementIsRejected() {
        val consensus = SlopeConsensus.combine(
            listOf(
                report(-2.0f),
                report(-2.1f),
                report(2.0f),
                report(2.1f),
                report(0.02f)
            )
        )
        assertNull(consensus)
    }

    @Test
    fun fieldModeRejectsThreeToTwoAndAcceptsFourToOne() {
        val weak = SlopeConsensus.combine(
            listOf(
                report(-2.0f),
                report(-2.2f),
                report(-2.1f),
                report(2.1f),
                report(2.2f)
            ),
            minAgree = 4
        )
        assertNull(weak)

        val strong = SlopeConsensus.combine(
            listOf(
                report(-2.0f),
                report(-2.2f),
                report(-2.1f),
                report(-2.3f),
                report(2.2f)
            ),
            minAgree = 4
        )
        assertTrue(strong != null)
        assertTrue(strong!!.overallCrossPercent < 0f)
    }
    @Test
    fun flatFloorBiasIsSuppressed() {
        val consensus = SlopeConsensus.combine(
            listOf(
                report(0.32f),
                report(0.41f),
                report(0.47f),
                report(0.38f),
                report(0.45f)
            ),
            minAgree = 4
        )
        assertTrue(consensus != null)
        assertEquals(0f, consensus!!.overallCrossPercent, 0.001f)
        assertTrue(consensus.segments.all { kotlin.math.abs(it.crossPercent) < 0.001f })
    }

    @Test
    fun weakSlopeNeedsUnanimousDirection() {
        val consensus = SlopeConsensus.combine(
            listOf(
                report(0.82f),
                report(0.77f),
                report(0.88f),
                report(0.79f),
                report(-0.68f)
            ),
            minAgree = 4
        )
        assertTrue(consensus != null)
        assertEquals(0f, consensus!!.overallCrossPercent, 0.001f)
    }

    @Test
    fun clearSlopeSurvivesFlatGuard() {
        val consensus = SlopeConsensus.combine(
            listOf(
                report(-1.7f),
                report(-1.8f),
                report(-1.6f),
                report(-1.9f),
                report(0.2f)
            ),
            minAgree = 4
        )
        assertTrue(consensus != null)
        assertTrue(consensus!!.overallCrossPercent < -1.5f)
    }
}
