package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.hypot

/**
 * Diagnostics separate the two endpoint marker/Depth offsets. A delta-only
 * audit can miss two anchors displaced by the SAME amount. Neither source
 * is physical ground truth, and this does not move markers or modify quality.
 */
object PrecisionMarkerFloorOffsetAudit {
    data class Result(
        val ballCells: Int,
        val cupCells: Int,
        val ballDepthHeightM: Float?,
        val cupDepthHeightM: Float?,
        val ballMarkerMinusDepthCm: Float?,
        val cupMarkerMinusDepthCm: Float?
    ) {
        fun diagnostic(): String {
            fun fmt(value: Float?): String =
                if (value == null || !value.isFinite()) "NA"
                else String.format(java.util.Locale.US,"%.2f",value)
            return "MARKER_ENDPOINT_OFFSETS_V1" +
                " ballCells=" + ballCells +
                " cupCells=" + cupCells +
                " ballDepthHeightCm=" + fmt(ballDepthHeightM?.times(100f)) +
                " cupDepthHeightCm=" + fmt(cupDepthHeightM?.times(100f)) +
                " ballMarkerMinusDepthCm=" + fmt(ballMarkerMinusDepthCm) +
                " cupMarkerMinusDepthCm=" + fmt(cupMarkerMinusDepthCm) +
                " diagnosticOnly=true groundTruth=false"
        }
    }

    fun evaluate(surface: PrecisionSurfaceModel?, ball: Vec3, cup: Vec3): Result {
        val unavailable = Result(0,0,null,null,null,null)
        if (surface == null || surface.groundCellCount < 25) return unavailable
        val dx=cup.x-ball.x
        val dz=cup.z-ball.z
        val length=hypot(dx,dz)
        if (!length.isFinite() || length < 0.40f) return unavailable
        val fx=dx/length
        val fz=dz/length
        val ballYs=ArrayList<Float>()
        val cupYs=ArrayList<Float>()
        val nearRadius=0.16f
        for (cell in surface.cells) {
            if (!cell.height.isFinite() || !cell.x.isFinite() || !cell.z.isFinite())
                continue
            val rx=cell.x-ball.x
            val rz=cell.z-ball.z
            val along=rx*fx+rz*fz
            val lateral=abs(-rx*fz+rz*fx)
            if (lateral > 0.18f) continue
            if (abs(along) <= nearRadius) ballYs.add(cell.height)
            if (abs(along-length) <= nearRadius) cupYs.add(cell.height)
        }
        fun median(xs: List<Float>): Float? {
            if (xs.size < 6) return null
            val sorted=xs.sorted()
            val n=sorted.size
            return if (n%2==0) (sorted[n/2-1]+sorted[n/2])*0.5f else sorted[n/2]
        }
        val by=median(ballYs)
        val cy=median(cupYs)
        return Result(ballYs.size,cupYs.size,by,cy,
            by?.let { (ball.y-it)*100f },
            cy?.let { (cup.y-it)*100f }
        )
    }
}
