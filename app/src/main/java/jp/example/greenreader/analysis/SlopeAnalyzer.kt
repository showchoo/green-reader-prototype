package jp.example.greenreader.analysis

import kotlin.math.abs
import kotlin.math.sqrt

object SlopeAnalyzer {
    fun analyze(points: List<Vec3>, ball: Vec3, cup: Vec3, corridorHalfWidthM: Float = 0.65f, bins: Int = 8): SlopeReport? {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val dist = sqrt(dx * dx + dz * dz)
        if (dist < 0.4f) return null
        val ux = dx / dist
        val uz = dz / dist
        val vx = -uz
        val vz = ux

        data class P(val s: Float, val t: Float, val h: Float)
        val corridor = points.mapNotNull { p ->
            val rx = p.x - ball.x
            val rz = p.z - ball.z
            val s = rx * ux + rz * uz
            val t = rx * vx + rz * vz
            if (s in -0.25f..(dist + 0.25f) && abs(t) <= corridorHalfWidthM) P(s, t, p.y) else null
        }
        if (corridor.size < 80) return null

        val segments = (0 until bins).mapNotNull { i ->
            val a = dist * i / bins
            val b = dist * (i + 1) / bins
            val local = corridor.filter { it.s in a..b }
            if (local.size < 8) null else {
                val fit = fitPlane(local.map { Triple(it.s, it.t,it.h) }) ?: return@mapNotNull null
                val mid = (a + b) * 0.5f
                val elev = fit.first * mid + fit.third
                SlopeSegment(a,b, fit.first * 100f, fit.second * 100f, elev, local.size)
            }
        }
        if (segments.isEmpty()) return null

        val allFit = fitPlane(corridor.map { Triple(it.s,it.t,it.h) }) ?: return null
        return SlopeReport(dist, segments, allFit.first * 100f, allFit.second * 100f, corridor.size)
    }

    private fun fitPlane(data: List<Triple<Float,Float,Float>>): Triple<Float,Float,Float>? {
        var ss=0.0; var tt=0.0; var st=0.0; var s=0.0; var t=0.0; var h=0.0; var sh=0.0; var th=0.0
        val n=data.size.toDouble()
        for ((sv,tv,hv) in data) {
            val sd=sv.toDouble(); val td=tv.toDouble(); val hd=hv.toDouble()
            ss+=sd*sd; tt+=td*td; st+=sd*td; s+=sd; t+=td; h+=hd; sh+=sd*hd; th+=td*hd
        }
        val a = arrayOf(
            doubleArrayOf(ss, st, s, sh),
            doubleArrayOf(st, tt, t, th),
            doubleArrayOf(s, t, n, h)
        )
        for (col in 0..2) {
            var pivot=col
            for (r in col+1..2) if (kotlin.math.abs(a[r][col]) > kotlin.math.abs(a[pivot][col])) pivot=r
            if (kotlin.math.abs(a[pivot][col]) < 1e-9) return null
            val tmp=a[col]; a[col]=a[pivot]; a[pivot]=tmp
            val d=a[col][col]; for (c in col..3) a[col][c]/=d
            for (r in 0..2) if (r!=col) {
                val f=a[r][col]
                for (c in col..3) a[r][c]-=f*a[col][c]
            }
        }
        return Triple(a[0][3].toFloat(),a[1][3].toFloat(),a[2][3].toFloat())
    }
}
