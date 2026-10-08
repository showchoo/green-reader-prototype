package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class PrecisionViewGeometryTelemetryTest {
    private fun record(
        source: String,
        basis: String,
        fx: Float = 250f
    ) = PrecisionFramePoseTelemetry.Entry(
        depthTimestampNs = 12345L,
        cameraFrameTimestampNs = 12500L,
        source = source,
        x = 0.3f, y = 0.9f, z = -0.4f,
        qx = 0f, qy = 0f, qz = 0f, qw = 1f,
        forwardLocalX = 0f, forwardLocalY = -0.8f, forwardLocalZ = -0.6f,
        rightLocalX = 1f, rightLocalY = 0f, rightLocalZ = 0f,
        projectionBasis = basis,
        projectionWidth = 640,
        projectionHeight = 480,
        focalX = fx,
        focalY = 260f,
        principalX = 320f,
        principalY = 240f
    )

    @Test fun rawAndFullKeepDistinctPixelBases() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        b.record(record("raw", "raw_texture_scaled"))
        b.record(record("full", "cpu_image_pixels"))
        val rows = b.toDiagnosticText().lines()
        assertTrue(rows.any { it.contains("camera_forward_local_x") })
        assertTrue(rows.any { it.contains("projection_basis,projection_width,projection_height") })
        assertEquals(2, b.size())
        assertTrue(rows.any { it.contains(",raw_texture_scaled,640,480,250.000000,260.000000,") })
        assertTrue(rows.any { it.contains(",cpu_image_pixels,640,480,250.000000,260.000000,") })
        assertTrue(rows.any { it.contains("0.000000,-0.800000,-0.600000,1.000000") })
    }

    @Test fun invalidCameraProjectionDoesNotAppearAsGoodTelemetry() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        b.record(record("raw", "raw_texture_scaled", fx = 0f))
        b.record(record("raw", "raw_texture_scaled", fx = Float.NaN))
        b.record(record("full", "cpu_image_pixels").copy(projectionHeight = -1))
        b.record(record("raw", "arbitrary"))
        assertEquals(0, b.size())
        assertTrue(b.toDiagnosticText().contains("records=0"))
    }

    @Test fun legacyPoseRecordsRemainParseable() {
        val b = PrecisionFramePoseTelemetry.Buffer()
        val legacy = record("raw", "raw_texture_scaled").copy(
            projectionBasis = "unknown", projectionWidth = 0, projectionHeight = 0
        )
        b.record(legacy)
        assertEquals(1, b.size())
    }
}
