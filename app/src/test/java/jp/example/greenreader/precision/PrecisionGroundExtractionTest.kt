package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class PrecisionGroundExtractionTest {
    private fun floorPoints(slopeForward: Float = 0f): List<PrecisionDepthPoint> {
        val out = ArrayList<PrecisionDepthPoint>()
        for (frame in 0 until 6) {
            for (xi in -10..10) {
                for (zi in 0..24) {
                    val x = xi * 0.10f
                    val z = zi * 0.10f
                    val deterministicNoise = (((xi * 17 + zi * 13 + frame * 7) % 7) - 3) * 0.0007f
                    val y = slopeForward * z + deterministicNoise
                    out += PrecisionDepthPoint(x, y, z, 0.9f, frame.toLong())
                }
            }
        }
        return out
    }

    @Test
    fun flatFloorRejectsFurnitureAndWallGeometry() {
        val points = floorPoints().toMutableList()

        // Horizontal furniture surface 65 cm above the floor.
        for (frame in 0 until 6) {
            for (xi in -5..5) {
                for (zi in 5..15) {
                    points += PrecisionDepthPoint(
                        xi * 0.10f,
                        0.65f,
                        zi * 0.10f,
                        0.95f,
                        (100 + frame).toLong()
                    )
                }
            }
        }

        // Vertical wall-like returns with many different heights.
        for (frame in 0 until 6) {
            for (xi in -10..10) {
                for (hi in 0..12) {
                    points += PrecisionDepthPoint(
                        xi * 0.10f,
                        hi * 0.08f,
                        2.2f,
                        0.9f,
                        (200 + frame).toLong()
                    )
                }
            }
        }

        val surface = PrecisionSurfaceBuilder.build(points)
        assertTrue(surface.groundCellCount > 200)
        assertTrue(surface.rejectedCellCount > 0)
        assertTrue(surface.cells.all { abs(it.height) < 0.10f })

        val report = PrecisionSlopeAnalyzer.analyze(
            surface,
            Vec3(0f, 0f, 0f),
            Vec3(0f, 0f, 2.0f)
        )
        assertTrue(report != null)
        assertEquals(0f, report!!.overallCrossPercent, 0.35f)
        assertEquals(0f, report.overallLongitudinalPercent, 0.35f)
    }

    @Test
    fun twoPercentSlopeIsPreserved() {
        val surface = PrecisionSurfaceBuilder.build(floorPoints(0.02f))
        val report = PrecisionSlopeAnalyzer.analyze(
            surface,
            Vec3(0f, 0f, 0f),
            Vec3(0f, 0.04f, 2.0f)
        )
        assertTrue(report != null)
        assertEquals(2.0f, report!!.overallLongitudinalPercent, 0.35f)
        assertEquals(0f, report.overallCrossPercent, 0.35f)
    }

    @Test
    fun absurdSteepReconstructionDoesNotProduceAimResult() {
        val surface = PrecisionSurfaceBuilder.build(
            floorPoints(0.20f),
            maxExpectedGrade = 0.30f
        )
        val report = PrecisionSlopeAnalyzer.analyze(
            surface,
            Vec3(0f, 0f, 0f),
            Vec3(0f, 0.40f, 2.0f)
        )
        assertTrue(report == null)
    }
}
