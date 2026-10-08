package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.SlopeSegment
import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionQualityEstimatorTest {
    private fun syntheticSurface(): PrecisionSurfaceModel {
        val cells = ArrayList<PrecisionSurfaceCell>()
        var xi = 0
        while (xi <= 40) {
            val x = xi * 0.05f
            var zi = -6
            while (zi <= 6) {
                val z = zi * 0.05f
                val h = 0.01f * x + 0.02f * z
                cells += PrecisionSurfaceCell(
                    x = x,
                    z = z,
                    height = h,
                    confidence = 0.96f,
                    observations = 8,
                    madMeters = 0.002f
                )
                zi++
            }
            xi++
        }
        return PrecisionSurfaceModel(
            cells = cells,
            voxelSizeMeters = 0.05f,
            sourcePointCount = 12000,
            uniqueFrames = 20,
            candidateCellCount = cells.size + 20,
            rejectedCellCount = 20,
            groundCellCount = cells.size
        )
    }

    private fun report(longitudinal: Float, cross: Float): SlopeReport {
        val segments = (0 until 8).map { i ->
            SlopeSegment(
                startMeters = i * 0.25f,
                endMeters = (i + 1) * 0.25f,
                longitudinalPercent = longitudinal,
                crossPercent = cross,
                elevationMeters = i * 0.0025f,
                sampleCount = 40
            )
        }
        return SlopeReport(
            distanceMeters = 2.0f,
            segments = segments,
            overallLongitudinalPercent = longitudinal,
            overallCrossPercent = cross,
            pointCount = 12000
        )
    }

    @Test
    fun stableDenseSurfaceGetsHighConfidence() {
        val surface = syntheticSurface()
        val windows = listOf(
            report(1.00f, 2.00f),
            report(1.03f, 1.96f),
            report(0.98f, 2.04f),
            report(1.01f, 2.02f),
            report(0.99f, 1.99f)
        )
        val collector = PrecisionDepthCollector.DiagnosticsSnapshot(
            attemptedFrames = 20,
            rawAcquiredFrames = 20,
            rawNonZeroPixels = 50000,
            confidencePassedPixels = 42000,
            fullAcquiredFrames = 5,
            fullNonZeroPixels = 16000,
            transformedValidPoints = 30000,
            acceptedUniqueFrames = 20,
            pointCount = 12000,
            rawAcceptedFrames = 18,
            fullAcceptedFrames = 5
        )
        val tracking = PrecisionTrackingMonitor.Snapshot(
            totalFrames = 80,
            trackingFrames = 80,
            failedTrackingFrames = 0,
            poseJumpCount = 0,
            maxTranslationStepMeters = 0.02f,
            maxRotationStepDegrees = 2.0f,
            cameraTravelMeters = 0.32f
        )

        val q = PrecisionQualityEstimator.evaluate(
            surface = surface,
            report = report(1.0f, 2.0f),
            windowReports = windows,
            collectorWindows = listOf(collector),
            tracking = tracking,
            ball = Vec3(0f, 0f, 0f),
            cup = Vec3(2f, 0.02f, 0f),
            temporalCheckVerified = true
        )

        assertEquals(PrecisionQualityEstimator.TIER_HIGH_PRECISION, q.tier)
        assertTrue(q.score >= 85)
        assertTrue(q.estimatedSlopeUncertaintyPercent <= 0.40f)
        assertTrue(q.corridorCoverage >= 0.875f)
    }

    @Test
    fun missingSurfaceAndTrackingGetsLowConfidence() {
        val q = PrecisionQualityEstimator.evaluate(
            surface = null,
            report = null,
            windowReports = emptyList(),
            collectorWindows = emptyList(),
            tracking = PrecisionTrackingMonitor.Snapshot(
                totalFrames = 20,
                trackingFrames = 4,
                failedTrackingFrames = 16,
                poseJumpCount = 2,
                cameraTravelMeters = 0.02f
            ),
            ball = Vec3(0f, 0f, 0f),
            cup = Vec3(2f, 0f, 0f),
            temporalCheckVerified = false
        )

        assertEquals(PrecisionQualityEstimator.TIER_LOW_CONFIDENCE, q.tier)
        assertTrue(q.score < 65)
        assertTrue(q.guidance.isNotEmpty())
    }
}
