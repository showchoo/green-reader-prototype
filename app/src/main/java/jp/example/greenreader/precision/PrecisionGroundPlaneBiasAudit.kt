package jp.example.greenreader.precision

import java.util.Locale
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Diagnostic-only, independent robust y = ax + bz + c fits to Raw/Full data.
 * Local xyz uses the ball's marker yaw frame; y stays gravity aligned.
 * Neither fitted plane nor ARCore horizontal planes are survey ground truth.
 * Production point selection, slope and guidance are untouched.
 */
object PrecisionGroundPlaneBiasAudit {
    private const val MAX_POINTS = 22000
    private const val NEAR_BALL_RADIUS_M = 0.42f
    private const val MAX_HORIZONTAL_RADIUS_M = 1.55f
    private const val HEIGHT_ENVELOPE_M = 0.36f
    private const val HEIGHT_BAND_M = 0.14f

    data class Fit(
        val supported: Boolean,
        val points: Int,
        val frames: Int,
        val xSpanM: Float = 0f,
        val zSpanM: Float = 0f,
        val slopeXPct: Float = Float.NaN,
        val slopeZPct: Float = Float.NaN,
        val interceptAtBallM: Float = Float.NaN,
        val rmsMm: Float = Float.NaN
    ) {
        val tiltPct: Float
            get() = if (supported) hypot(slopeXPct, slopeZPct) else Float.NaN
    }

    data class PlaneObservation(
        val planeUpdates: Int = 0,
        val trackedNearBallUpdates: Int = 0,
        val available: Boolean = false,
        val slopeXPct: Float = Float.NaN,
        val slopeZPct: Float = Float.NaN,
        val heightAtBallM: Float = Float.NaN,
        val markerInsideExtents: Boolean = false
    )

    private data class P(val x: Float, val y: Float, val z: Float, val t: Long)

    private fun median(xs: List<Float>): Float {
        val s = xs.sorted()
        return if (s.size % 2 == 0)
            (s[s.size / 2 - 1] + s[s.size / 2]) / 2f
        else s[s.size / 2]
    }

    private data class Regression(val ax: Double, val bz: Double, val intercept: Double) {
        fun prediction(p: P): Double = ax*p.x + bz*p.z + intercept
    }

    private fun regression(points: List<P>): Regression? {
        if (points.size < 40) return null
        val n = points.size.toDouble()
        val mx = points.sumOf { it.x.toDouble() } / n
        val mz = points.sumOf { it.z.toDouble() } / n
        val my = points.sumOf { it.y.toDouble() } / n
        var xx = 0.0; var zz = 0.0; var xz = 0.0
        var xy = 0.0; var zy = 0.0
        for (p in points) {
            val dx = p.x-mx; val dz = p.z-mz; val dy = p.y-my
            xx += dx*dx; zz += dz*dz; xz += dx*dz
            xy += dx*dy; zy += dz*dy
        }
        val det = xx*zz - xz*xz
        // Reject narrow line-like point arrangements, including high-N ones.
        if (!det.isFinite() || det/n/n < 0.000008) return null
        val ax = (xy*zz - zy*xz)/det
        val bz = (zy*xx - xy*xz)/det
        val intercept = my - ax*mx - bz*mz
        return if (ax.isFinite() && bz.isFinite() && intercept.isFinite())
            Regression(ax,bz,intercept) else null
    }

    fun fit(points: List<PrecisionDepthPoint>, source: String): Fit {
        require(source == "raw" || source == "full")
        val stride = max(1, (points.size + MAX_POINTS - 1) / MAX_POINTS)
        val candidates = ArrayList<P>(min(points.size / stride, MAX_POINTS))
        val nearHeights = ArrayList<Float>()
        for (i in points.indices step stride) {
            val p = points[i]
            if (p.depthSource != source || !p.x.isFinite() ||
                !p.y.isFinite() || !p.z.isFinite() || p.confidence < 0.5f) continue
            val radius = hypot(p.x, p.z)
            if (radius > MAX_HORIZONTAL_RADIUS_M || abs(p.y) > HEIGHT_ENVELOPE_M)
                continue
            candidates.add(P(p.x, p.y, p.z, p.frameTimestampNs))
            if (radius <= NEAR_BALL_RADIUS_M) nearHeights.add(p.y)
        }
        if (nearHeights.size < 18) return Fit(false, candidates.size, 0)
        val reference = median(nearHeights)
        val nearGround = candidates.filter { abs(it.y-reference) <= HEIGHT_BAND_M }
        if (nearGround.size < 150) return Fit(false,nearGround.size,0)
        val initial = regression(nearGround) ?: return Fit(false,nearGround.size,0)
        val residuals = nearGround.map {
            abs(it.y-initial.prediction(it).toFloat())
        }
        val mad = median(residuals)
        val maxResidual = (3f*1.4826f*mad).coerceIn(0.020f,0.070f)
        val inliers = nearGround.filter {
            abs(it.y-initial.prediction(it).toFloat()) <= maxResidual
        }
        if (inliers.size < 120) return Fit(false,inliers.size,0)
        val timestamps = inliers.asSequence().map { it.t }.distinct().take(3).count()
        val minX = inliers.minOf { it.x }; val maxX = inliers.maxOf { it.x }
        val minZ = inliers.minOf { it.z }; val maxZ = inliers.maxOf { it.z }
        val spanX = maxX-minX; val spanZ = maxZ-minZ
        if (timestamps < 3 || spanX < 0.28f || spanZ < 0.28f)
            return Fit(false,inliers.size,timestamps,spanX,spanZ)
        val final = regression(inliers)
            ?: return Fit(false,inliers.size,timestamps,spanX,spanZ)
        val squared = inliers.sumOf {
            val error = it.y-final.prediction(it)
            error*error
        }
        return Fit(true,inliers.size,timestamps,spanX,spanZ,
            (final.ax*100.0).toFloat(),(final.bz*100.0).toFloat(),
            final.intercept.toFloat(),(sqrt(squared/inliers.size)*1000.0).toFloat())
    }

    private fun fmt(value: Float, scale: Float = 1f): String =
        if (value.isFinite()) String.format(Locale.US,"%.2f",value*scale)
        else "NA"

    fun diagnostic(points: List<PrecisionDepthPoint>, ar: PlaneObservation): String {
        val raw = fit(points,"raw")
        val full = fit(points,"full")
        val rawFullDelta = if (raw.supported && full.supported)
            hypot(raw.slopeXPct-full.slopeXPct,raw.slopeZPct-full.slopeZPct)
            else Float.NaN
        val rawArDelta = if (raw.supported && ar.available)
            hypot(raw.slopeXPct-ar.slopeXPct,raw.slopeZPct-ar.slopeZPct)
            else Float.NaN
        val fullArDelta = if (full.supported && ar.available)
            hypot(full.slopeXPct-ar.slopeXPct,full.slopeZPct-ar.slopeZPct)
            else Float.NaN
        fun fitLine(name:String,f:Fit):String =
            " "+name+"Valid="+f.supported+
            " "+name+"N="+f.points+" "+name+"Frames="+f.frames+
            " "+name+"SpanXcm="+fmt(f.xSpanM,100f)+
            " "+name+"SpanZcm="+fmt(f.zSpanM,100f)+
            " "+name+"SlopeXPct="+fmt(f.slopeXPct)+
            " "+name+"SlopeZPct="+fmt(f.slopeZPct)+
            " "+name+"TiltPct="+fmt(f.tiltPct)+
            " "+name+"AtBallHeightCm="+fmt(f.interceptAtBallM,100f)+
            " "+name+"RmsMm="+fmt(f.rmsMm)
        return "GROUND_PLANE_BIAS_V1"+
            fitLine("raw",raw)+fitLine("full",full)+
            " arPlaneUpdated="+ar.planeUpdates+
            " arNearBallUpdated="+ar.trackedNearBallUpdates+
            " arAvailable="+ar.available+
            " arInsideExtents="+ar.markerInsideExtents+
            " arSlopeXPct="+fmt(ar.slopeXPct)+
            " arSlopeZPct="+fmt(ar.slopeZPct)+
            " arAtBallHeightCm="+fmt(ar.heightAtBallM,100f)+
            " rawFullTiltDisagreementPct="+fmt(rawFullDelta)+
            " rawArTiltDisagreementPct="+fmt(rawArDelta)+
            " fullArTiltDisagreementPct="+fmt(fullArDelta)+
            " diagnosticOnly=true groundTruth=false"
    }
}
