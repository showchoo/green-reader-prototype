package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class PrecisionFramePoseTelemetryTest {
    private fun entry(depth: Long, frame: Long = depth, source: String = "raw") =
        PrecisionFramePoseTelemetry.Entry(
            depthTimestampNs = depth, cameraFrameTimestampNs = frame,
            source = source, x = .1f, y = .2f, z = .3f,
            qx = 0f, qy = 0f, qz = 0f, qw = 1f
        )

    @Test fun savesBothTimestampsAndSourceForOfflineLatencyCheck() {
        val buffer = PrecisionFramePoseTelemetry.Buffer()
        buffer.record(entry(101L, 120L))
        buffer.record(entry(101L, 120L, "full"))
        val log = buffer.toDiagnosticText()
        assertTrue(log.startsWith("FRAME_POSE_V1_BEGIN records=2 dropped=0\n"))
        assertTrue(log.contains("101,120,raw,"))
        assertTrue(log.contains("101,120,full,"))
        assertTrue(log.endsWith("FRAME_POSE_V1_END"))
    }

    @Test fun duplicateSourceAndDepthTimestampDoesNotInflateEvidence() {
        val buffer = PrecisionFramePoseTelemetry.Buffer()
        buffer.record(entry(101))
        buffer.record(entry(101))
        assertEquals(1, buffer.size())
        assertEquals(0, buffer.droppedCount())
    }

    @Test fun boundedStorageDropsOldestAndResetClearsSession() {
        val buffer = PrecisionFramePoseTelemetry.Buffer(2)
        buffer.record(entry(11))
        buffer.record(entry(22))
        buffer.record(entry(33))
        assertEquals(2, buffer.size())
        assertEquals(1, buffer.droppedCount())
        assertFalse(buffer.toDiagnosticText().contains("11,11,raw,"))
        buffer.clear()
        assertEquals(0, buffer.size())
        assertEquals(0, buffer.droppedCount())
        assertTrue(buffer.toDiagnosticText().contains("records=0 dropped=0"))
    }

    @Test fun malformedPosesAndUnknownSourceNeverPoisonLog() {
        val buffer = PrecisionFramePoseTelemetry.Buffer()
        buffer.record(entry(4, source="unknown"))
        buffer.record(entry(5).copy(x=Float.NaN))
        assertEquals(0, buffer.size())
    }
}
