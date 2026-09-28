package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import org.junit.Assert.*
import org.junit.Test

class PrecisionMarkerCandidateGateTest {
    private val camera = Vec3(0f, 0f, 0f)

    @Test fun reportedCupIsRejectedBeforeSourceSelection() {
        val ball = Vec3(-0.088341296f, -0.46506894f, -0.9961827f)
        val cup = Vec3(-0.044462323f, -0.17497732f, -1.0839884f)
        val result = PrecisionMarkerCandidateGate.evaluate(camera, cup, ball)
        assertEquals("vertical-mismatch", result.reason)
        assertEquals(0.098f, result.horizontal!!, 0.001f)
        assertEquals(0.290f, result.vertical!!, 0.001f)
        assertEquals(0.080f, result.limit!!, 0.00001f)
        assertFalse(result.accepted)
        // A later, level ground candidate remains eligible without moving the
        // first candidate onto an invented plane or relaxing its height bound.
        val ground = Vec3(-0.044f, ball.y - 0.04f, -2.1f)
        assertTrue(PrecisionMarkerCandidateGate.evaluate(camera, ground, ball).accepted)
    }

    @Test fun ballHasDistanceGateButNoInventedHeightReference() {
        assertTrue(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(0f, -0.46f, -1f)).accepted)
        assertFalse(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(0f, 0f, -4.01f)).accepted)
        assertFalse(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(0f, 0f, -0.1f)).accepted)
    }

    @Test fun axialDepthBelowFourMetersDoesNotBypassEuclideanGate() {
        assertFalse(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(3f, 0f, -3f)).accepted)
    }

    @Test fun pairGateIsSymmetricAndRejectsNonfiniteInputs() {
        val ball = Vec3(0f, -0.5f, -1f)
        assertTrue(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(0f, -0.35f, -2f), ball).accepted)
        assertTrue(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(0f, -0.65f, -2f), ball).accepted)
        assertFalse(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(0f, -0.33f, -2f), ball).accepted)
        assertFalse(PrecisionMarkerCandidateGate.evaluate(camera, Vec3(Float.NaN, 0f, -1f), ball).accepted)
        assertFalse(PrecisionMarkerCandidateGate.evaluate(camera, ball, Vec3(0f, Float.NaN, -1f)).accepted)
    }

    @Test fun pairGateIsInvariantUnderWorldTranslation() {
        val ball = Vec3(0.1f, -0.5f, -1f)
        val cup = Vec3(0.15f, -0.45f, -2f)
        fun shift(v: Vec3) = Vec3(v.x + 7f, v.y - 2f, v.z + 3f)
        val a = PrecisionMarkerCandidateGate.evaluate(camera, cup, ball)
        val b = PrecisionMarkerCandidateGate.evaluate(shift(camera), shift(cup), shift(ball))
        assertEquals(a.accepted, b.accepted)
        assertEquals(a.horizontal!!, b.horizontal!!, 0.00001f)
        assertEquals(a.vertical!!, b.vertical!!, 0.00001f)
    }
}
