package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class PrecisionDepthPoseLagTest {
    private fun entry(
        timestamp: Long = 1_000_000_000L,
        currentFrame: Long = 1_120_000_000L,
        currentX: Float = .20f
    ) = PrecisionFramePoseTelemetry.Entry(
        depthTimestampNs = timestamp,
        cameraFrameTimestampNs = currentFrame,
        source = "raw",
        x = currentX, y = 1f, z = 0f,
        qx = 0f, qy = 0f, qz = 0f, qw = 1f,
        forwardLocalX = 0f, forwardLocalY = 0f, forwardLocalZ = -1f
    )

    private fun tracked(timestamp: Long, x: Float, fz: Float = -1f,
                        fx: Float = 0f) =
        PrecisionFramePoseTelemetry.CameraFramePose(
            frameTimestampNs = timestamp, x = x, y = 1f, z = 0f,
            forwardX = fx, forwardY = 0f, forwardZ = fz
        )

    @Test fun matchesDepthTimeNotCurrentFrameTime() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        b.recordCameraFrame(tracked(1_000_000_000L, x = 0f))
        b.recordCameraFrame(tracked(1_120_000_000L, x = .20f))
        val depth = entry()
        b.record(depth)
        val m = b.nearestFrameFor(depth)!!
        assertEquals(1_000_000_000L, m.frameTimestampNs)
        assertEquals(0.0, m.absoluteTimeGapMs, 0.00001)
        assertEquals(0.20, m.translationDeltaM, 0.00001)
        assertEquals(0.0, m.forwardDeltaDegrees, 0.00001)
        val log = b.toDiagnosticText()
        assertTrue(log.contains("nearest_camera_frame_timestamp_ns,nearest_camera_gap_ms"))
        assertTrue(log.contains("1000000000,0.000000,0.200000,0.000000"))
    }

    @Test fun ifOnlyStaleFramesExistTheMotionEstimateIsMissingNotZero() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        b.recordCameraFrame(tracked(1_200_000_000L, x = 0f))
        val depth = entry()
        assertNull(b.nearestFrameFor(depth))
        b.record(depth)
        val log = b.toDiagnosticText()
        assertTrue(log.contains("FRAME_POSE_V1_BEGIN records=1 dropped=0\n"))
        assertTrue(log.contains(",,,")) // four truly blank motion fields
    }

    @Test fun cameraRotationDifferenceIsRecordedWithoutChangingDepthVerdict() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        b.recordCameraFrame(tracked(1_000_000_000L, x=0f, fz=0f, fx=1f))
        val m = b.nearestFrameFor(entry(currentX=0f))!!
        assertEquals(90.0, m.forwardDeltaDegrees, 0.00001)
    }

    @Test fun historyIsBoundedAndFullyResetWithEachScanWindow() {
        val b = PrecisionFramePoseTelemetry.Buffer(maxRecords=4, maxCameraFrames=2)
        b.recordCameraFrame(tracked(1_000_000_000L, x=0f))
        b.recordCameraFrame(tracked(1_010_000_000L, x=0f))
        b.recordCameraFrame(tracked(1_020_000_000L, x=0f))
        assertEquals(2, b.cameraFrameCount())
        assertNull(b.nearestFrameFor(entry(timestamp=1_000_000_000L),
                                    maxGapNs=1_000_000L))
        b.clear()
        assertEquals(0, b.cameraFrameCount())
        assertEquals(0, b.size())
    }

    @Test fun duplicateAndMalformedTrackedFrameAreDiscarded() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        b.recordCameraFrame(tracked(0L, x=0f))
        b.recordCameraFrame(tracked(1_000_000_000L, x=Float.NaN))
        b.recordCameraFrame(tracked(1_000_000_000L, x=0f))
        b.recordCameraFrame(tracked(1_000_000_000L, x=.30f))
        assertEquals(1, b.cameraFrameCount())
        val m = b.nearestFrameFor(entry(currentX=0f))!!
        assertEquals(0.0, m.translationDeltaM, 0.00001)
    }
}
