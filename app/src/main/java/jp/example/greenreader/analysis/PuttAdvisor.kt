package jp.example.greenreader.analysis

import kotlin.math.sqrt

object PuttAdvisor {
    /**
     * aimOffsetCm: positive = uphill side of the cross-slope coordinate.
     * The UI currently maps positive to the left side of the displayed putt line.
     *
     * Important physics convention:
     *  - crossPercent is dh/dt, so its sign points toward HIGHER ground.
     *  - gravity makes the ball break toward -dh/dt (downhill).
     *  - therefore the starting aim offset should be toward +dh/dt (uphill),
     *    not toward the downhill side.
     */
    data class Advice(val aimOffsetCm: Float, val effectiveDistanceM: Float, val warning: String)

    fun advise(report: SlopeReport, stimp: Float, grain: GrainReport?): Advice {
        val d = report.distanceMeters
        val speedFactor = (stimp / 9f).coerceIn(0.65f, 1.45f)
        val cross = report.segments.map { it.crossPercent }.average().toFloat() / 100f
        val long = report.segments.map { it.longitudinalPercent }.average().toFloat() / 100f
        val t = sqrt((2f * d) / (1.25f / speedFactor)).coerceIn(0.5f, 5f)

        // Magnitude of lateral gravity effect. cross>0 means the +t side is higher,
        // so the ball itself wants to break toward -t. To compensate, AIM uphill (+t).
        var uphillAim = 0.5f * 9.80665f * cross * t * t * 0.18f
        val grainConfidence = grain?.confidence ?: 0f
        if (grainConfidence > 0.45f) uphillAim *= 1f + 0.08f * grainConfidence

        val effective = d * (1f + long * 3.0f).coerceIn(0.65f, 1.5f)
        return Advice(
            aimOffsetCm = uphillAim * 100f,
            effectiveDistanceM = effective,
            warning = "実験値。矢印は下り方向、狙い点はその反対の上り側です。実グリーンでキャリブレーションするまで狙い量は参考表示です。"
        )
    }
}
