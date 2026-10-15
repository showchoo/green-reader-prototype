package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionProjectionRayAuditTest {
    @Test fun centeredDepthPixelMapsToForwardCameraAxis() {
        val ray = PrecisionProjectionRayAudit.cameraRay(
            100f, 50f, 2f, 200f, 200f, 100f, 50f
        )
        requireNotNull(ray)
        assertEquals(0f, ray[0], 0.00001f)
        assertEquals(0f, ray[1], 0.00001f)
        assertEquals(-2f, ray[2], 0.00001f)
    }

    @Test fun cameraRayYSignAndScalingAreCorrect() {
        val ray = PrecisionProjectionRayAudit.cameraRay(
            110f, 70f, 2f, 200f, 100f, 100f, 50f
        )
        requireNotNull(ray)
        assertEquals(0.10f, ray[0], 0.00001f)
        assertEquals(-0.40f, ray[1], 0.00001f)
        assertEquals(-2f, ray[2], 0.00001f)
    }

    @Test fun invalidIntrinsicsAndDepthAreRejected() {
        assertNull(PrecisionProjectionRayAudit.cameraRay(
            1f, 1f, 0f, 200f, 200f, 10f, 10f
        ))
        assertNull(PrecisionProjectionRayAudit.cameraRay(
            1f, 1f, 1f, 0f, 200f, 10f, 10f
        ))
        assertNull(PrecisionProjectionRayAudit.cameraRay(
            Float.NaN, 1f, 1f, 200f, 200f, 10f, 10f
        ))
    }

    @Test fun independentRawAndFullDiagnosticsNeverImplyGroundTruth() {
        val buffer=PrecisionProjectionRayAudit.Buffer()
        buffer.record("raw",PrecisionProjectionRayAudit.Probe(
            -1f, 4f, 1.0f, -28f
        ))
        buffer.record("raw",PrecisionProjectionRayAudit.Probe(
            -2f, 3f, 1.1f, -25f
        ))
        buffer.record("raw",PrecisionProjectionRayAudit.Probe(
            -3f, 2f, 1.2f, -22f
        ))
        buffer.record("full",PrecisionProjectionRayAudit.Probe(
            6f, 9f, 2.0f, -45f
        ))
        buffer.invalidMapping("raw")
        buffer.error()
        val r=buffer.summary("raw")
        assertEquals(3,r.count)
        assertEquals(1,r.invalidMappedPixels)
        assertEquals(-2f,r.medianSignedVerticalCm,0.0001f)
        assertEquals(2f,r.medianAbsVerticalCm,0.0001f)
        assertEquals(3f,r.p90AbsVerticalCm,0.0001f)
        assertEquals(-28f,r.minCameraPitchDeg,0.0001f)
        assertEquals(-22f,r.maxCameraPitchDeg,0.0001f)
        assertEquals(1,buffer.summary("full").count)
        val report=buffer.diagnostic()
        assertTrue(report.contains("rawSignedVerticalCm=-2.00"))
        assertTrue(report.contains("fullSignedVerticalCm=6.00"))
        assertTrue(report.contains("rawInvalidMap=1"))
        assertTrue(report.contains("transformErrors=1"))
        assertTrue(report.contains("diagnosticOnly=true groundTruth=false"))
    }

    @Test fun emptyAndClearedSamplesStayUndetermined() {
        val buffer=PrecisionProjectionRayAudit.Buffer()
        assertTrue(buffer.summary("raw").medianAbsVerticalCm.isNaN())
        buffer.record("raw",PrecisionProjectionRayAudit.Probe(
            0f,0f,1f,-12f
        ))
        buffer.record("unknown",PrecisionProjectionRayAudit.Probe(
            100f,100f,1f,0f
        ))
        assertEquals(1,buffer.summary("raw").count)
        buffer.clear()
        assertEquals(0,buffer.summary("raw").count)
        assertEquals(0,buffer.summary("full").count)
        assertTrue(buffer.diagnostic().contains("rawAbsVerticalCm=NA"))
        assertFalse(buffer.diagnostic().contains("rawN=1"))
    }
}
