package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionMarkerGeometryTest {
    @Test fun horizontalFloorIsPlausible() {
        val r = PrecisionMarkerGeometry.evaluate(Vec3(0f, 0f, 0f), Vec3(0f, 0f, -2f), 2f)
        assertEquals(2f, r.horizontalMeters, 0.0001f)
        assertEquals(0f, r.verticalMeters, 0.0001f)
        assertFalse(r.markerWarning)
        assertFalse(r.referenceWarning)
        assertFalse(r.needsReview)
    }

    @Test fun tallFakeCupPlaneIsFlagged() {
        val r = PrecisionMarkerGeometry.evaluate(
            Vec3(0f, 0f, 0f), Vec3(0f, 0.32f, -2.45f), 3f
        )
        assertTrue(r.markerWarning)
        assertTrue(r.referenceWarning)
        assertTrue(r.needsReview)
        assertEquals(-0.55f, r.referenceErrorMeters!!, 0.0001f)
    }

    @Test fun highButPhysicallyAllowedGreenGradeIsNotBlindlyRejected() {
        val r = PrecisionMarkerGeometry.evaluate(
            Vec3(0f, 0f, 0f), Vec3(0f, 0.24f, -2f)
        )
        assertEquals(12.0f, r.nominalGradePercent, 0.001f)
        assertFalse(r.markerWarning)
    }

    @Test fun referenceErrorChecksOnlyWhenProvided() {
        val ball = Vec3(0f, 0f, 0f)
        val cup = Vec3(0f, 0f, -1.83f)
        assertFalse(PrecisionMarkerGeometry.evaluate(ball, cup).referenceWarning)
        assertTrue(PrecisionMarkerGeometry.evaluate(ball, cup, 2f).referenceWarning)
        assertFalse(PrecisionMarkerGeometry.evaluate(ball, cup, 1.86f).referenceWarning)
    }

    @Test fun shortAndInvalidMarksAreRejected() {
        val ball = Vec3(0f, 0f, 0f)
        assertTrue(PrecisionMarkerGeometry.evaluate(ball, Vec3(0f, 0f, -0.2f)).markerWarning)
        assertTrue(PrecisionMarkerGeometry.evaluate(ball, Vec3(Float.NaN, 0f, -2f)).markerWarning)
    }
}
