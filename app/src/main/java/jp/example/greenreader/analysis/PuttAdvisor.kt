package jp.example.greenreader.analysis

import kotlin.math.sqrt

object PuttAdvisor {
    data class Advice(val aimOffsetCm: Float, val effectiveDistanceM: Float, val warning: String)

    fun advise(report: SlopeReport, stimp: Float, grain: GrainReport?): Advice {
        val d=report.distanceMeters
        val speedFactor=(stimp/9f).coerceIn(0.65f,1.45f)
        val cross=report.segments.map { it.crossPercent }.average().toFloat()/100f
        val long=report.segments.map { it.longitudinalPercent }.average().toFloat()/100f
        val t=sqrt((2f*d)/(1.25f/speedFactor)).coerceIn(0.5f,5f)
        var lateral=0.5f*9.80665f*cross*t*t*0.18f
        val grainConfidence=grain?.confidence ?: 0f
        if(grainConfidence>0.45f) lateral*=1f+0.08f*grainConfidence
        val effective=d*(1f+long*3.0f).coerceIn(0.65f,1.5f)
        return Advice(
            aimOffsetCm=-lateral*100f,
            effectiveDistanceM=effective,
            warning="実験値。実グリーンでキャリブレーションするまで狙い量は参考表示です。"
        )
    }
}
