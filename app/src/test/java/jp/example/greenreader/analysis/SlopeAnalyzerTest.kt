package jp.example.greenreader.analysis

import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SlopeAnalyzerTest {
    @Test
    fun sparseFarEndOutliersDoNotReverseUniformCrossSlope() {
        val points = mutableListOf<Vec3>()
        for (si in -5..45) {
            val s = si * 0.05f
            for (ti in -10..10) {
                val t = ti * 0.05f
                val noise = ((si * 17 + ti * 13) % 7) * 0.0003f
                points += Vec3(s, 0.02f * t + noise, t)
            }
        }

        // A minority of bad far-end depth points would pull an ordinary local fit
        // toward the opposite direction.
        for (si in 32..40) {
            val s = si * 0.05f
            for (ti in -10..10 step 4) {
                val t = ti * 0.05f
                points += Vec3(s, -0.10f * t + 0.08f, t)
            }
        }

        val report = SlopeAnalyzer.analyze(
            points = points,
            ball = Vec3(0f, 0f, 0f),
            cup = Vec3(2f, 0f, 0f),
            bins = 8
        )

        assertNotNull(report)
        assertTrue(report!!.overallCrossPercent > 0f)
        assertTrue(report.segments.isNotEmpty())
        assertTrue(report.segments.all { it.crossPercent > 0f })
    }

    @Test
    fun cleanStrongSlopeChangeIsStillPreserved() {
        val points = mutableListOf<Vec3>()
        for (si in -5..45) {
            val s = si * 0.05f
            for (ti in -12..12) {
                val t = ti * 0.05f
                val cross = if (s < 1f) 0.04f else -0.04f
                points += Vec3(s, cross * t, t)
            }
        }

        val report = SlopeAnalyzer.analyze(
            points = points,
            ball = Vec3(0f, 0f, 0f),
            cup = Vec3(2f, 0f, 0f),
            bins = 8
        )

        assertNotNull(report)
        assertTrue(report!!.segments.take(3).all { it.crossPercent > 0f })
        assertTrue(report.segments.takeLast(3).all { it.crossPercent < 0f })
    }

    @Test
    fun elevatedRoomGeometryDoesNotFlipRightDownGreen() {
        val points = mutableListOf<Vec3>()

        // Ball -> cup is +X, so +t is +Z. The green falls toward +Z (the
        // synthetic "right" side), therefore dh/dt must be negative.
        for (si in -5..45) {
            val s = si * 0.05f
            for (ti in -10..10) {
                val t = ti * 0.05f
                val noise = ((si * 11 + ti * 19) % 5) * 0.00025f
                points += Vec3(s, -0.03f * t + noise, t)
            }
        }

        // Simulate dense furniture/wall depth returns inside the same X/Z
        // corridor. They are well above the green and carry the opposite lateral
        // trend; they must not be allowed to reverse the putting surface.
        for (si in -5..45) {
            val s = si * 0.05f
            for (ti in -10..10) {
                val t = ti * 0.05f
                val layer = ((si + ti) and 3) * 0.08f
                points += Vec3(s, 0.65f + layer + 0.10f * t, t)
                points += Vec3(s, 1.05f + layer + 0.08f * t, t)
            }
        }

        val report = SlopeAnalyzer.analyze(
            points = points,
            ball = Vec3(0f, 0f, 0f),
            cup = Vec3(2f, 0f, 0f),
            bins = 8
        )

        assertNotNull(report)
        assertTrue("right-down surface must keep negative cross slope", report!!.overallCrossPercent < -1f)
        assertTrue(report.segments.count { it.crossPercent < 0f } >= 6)
    }
}
