package jp.example.greenreader.precision

import jp.example.greenreader.analysis.PuttAdvisor
import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.SlopeSegment
import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionDirectionSafetyTest {
    private fun report(cross: Float, segments: List<Float> = List(8) { cross }): SlopeReport =
        SlopeReport(
            distanceMeters = 2f,
            segments = segments.mapIndexed { i, c ->
                SlopeSegment(i * .25f, (i + 1) * .25f, 0f, c, 0f, 80)
            },
            overallLongitudinalPercent = 0f,
            overallCrossPercent = cross,
            pointCount = 20000
        )

    @Test fun rightDownhillGivesNegativeGradientAndLeftUphillAim() {
        // +cross is uphill; negative derivative -> right side lower.
        val slope = report(-3f)
        val verdict = PrecisionDirectionSafety.evaluate(
            slope, listOf(-2.8f, -3.1f, -3f, -2.9f).map { 0f to it }
        )
        assertTrue(verdict.trustworthy)
        val advice = PuttAdvisor.advise(slope, 9f, null)
        assertTrue("the starting aim should be uphill (-t)", advice.aimOffsetCm < 0f)
        assertTrue("the ball will break downhill (+t)", -slope.overallCrossPercent > 0f)
    }

    @Test fun leftDownhillGivesPositiveGradientAndRightUphillAim() {
        val slope = report(3f)
        val verdict = PrecisionDirectionSafety.evaluate(
            slope, listOf(2.8f, 3.1f, 3f, 2.9f).map { 0f to it }
        )
        assertTrue(verdict.trustworthy)
        assertTrue(PuttAdvisor.advise(slope, 9f, null).aimOffsetCm > 0f)
        assertTrue(-slope.overallCrossPercent < 0f)
    }

    @Test fun oppositeIndependentWindowsNeverClaimCertainHookOrSlice() {
        val verdict = PrecisionDirectionSafety.evaluate(
            report(3f), listOf(0f to 3f, 0f to -2f, 0f to 3.1f, 0f to -2.8f)
        )
        assertFalse(verdict.trustworthy)
        assertEquals("opposing-windows", verdict.reason)
    }

    @Test fun unresolvedNearFlatMustNotInventAVisibleDirection() {
        assertFalse(PrecisionDirectionSafety.evaluate(
            report(.3f), List(6) { 0f to .3f }
        ).trustworthy)
        assertFalse(PrecisionDirectionSafety.evaluate(
            report(3f), List(3) { 0f to 3f }
        ).trustworthy)
    }

    @Test fun strongOppositeSegmentsVetoOneSidedVisualBreak() {
        val slopes = listOf(3f, 3f, 3f, -2f, -3f, 3f, 3f, 3f)
        val verdict = PrecisionDirectionSafety.evaluate(
            report(3f, slopes), List(5) { 0f to 3f }
        )
        assertFalse(verdict.trustworthy)
        assertEquals("opposing-segments", verdict.reason)
    }

    @Test fun missingReportCannotHaveTrustedDirection() {
        assertFalse(PrecisionDirectionSafety.evaluate(null, List(5) { 0f to 2f }).trustworthy)
    }

    @Test fun mirroredBallCupDirectionChangesLocalCrossSignConsistently() {
        // A physical elevation field h = +0.03 * z:
        // ball -> cup +X gives +t along +Z, hence +3%.
        // The opposite putt direction gives +t along -Z, hence -3%.
        val model = PrecisionSurfaceModel(
            cells = (-10..50).flatMap { xi ->
                (-15..15).map { zi ->
                    val x = xi * .05f
                    val z = zi * .05f
                    PrecisionSurfaceCell(x, z, .03f * z, .95f, 12, .002f)
                }
            },
            voxelSizeMeters = .05f,
            sourcePointCount = 20000,
            uniqueFrames = 14
        )
        val alongX = PrecisionSlopeAnalyzer.analyze(model, Vec3(0f,0f,0f), Vec3(2f,0f,0f))
        val againstX = PrecisionSlopeAnalyzer.analyze(model, Vec3(2f,0f,0f), Vec3(0f,0f,0f))
        assertNotNull(alongX)
        assertNotNull(againstX)
        assertTrue(alongX!!.overallCrossPercent > 1.0f)
        assertTrue(againstX!!.overallCrossPercent < -1.0f)
    }
}
