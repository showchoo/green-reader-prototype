package jp.example.greenreader.analysis

import android.media.Image
import com.google.ar.core.Frame
import com.google.ar.core.exceptions.NotYetAvailableException
import kotlin.math.*

object GrainEstimator {
    fun estimate(frame: Frame): GrainReport? {
        try {
            frame.acquireCameraImage().use { image ->
                return estimateFromY(image)
            }
        } catch (_: NotYetAvailableException) {
            return null
        }
    }

    private fun estimateFromY(image: Image): GrainReport? {
        val p = image.planes[0]
        val b = p.buffer
        val w=image.width; val h=image.height
        val rs=p.rowStride; val ps=p.pixelStride
        val x0=(w*0.2).toInt(); val x1=(w*0.8).toInt()
        val y0=(h*0.35).toInt(); val y1=(h*0.8).toInt()
        val step=max(4,w/180)
        var jxx=0.0; var jyy=0.0; var jxy=0.0; var n=0
        fun lum(x:Int,y:Int):Int {
            val i=y*rs+x*ps
            return if(i in 0 until b.limit()) b.get(i).toInt() and 0xff else 0
        }
        for(y in y0+step until y1-step step step) for(x in x0+step until x1-step step step) {
            val gx=(lum(x+step,y)-lum(x-step,y)).toDouble()
            val gy=(lum(x,y+step)-lum(x,y-step)).toDouble()
            jxx+=gx*gx; jyy+=gy*gy; jxy+=gx*gy; n++
        }
        if(n<50) return null
        val trace=jxx+jyy
        val disc=sqrt(max(0.0,(jxx-jyy)*(jxx-jyy)+4*jxy*jxy))
        val lambda1=(trace+disc)/2; val lambda2=(trace-disc)/2
        val coherence=((lambda1-lambda2)/(lambda1+lambda2+1e-9)).coerceIn(0.0,1.0)
        val gradAngle=0.5*atan2(2*jxy,jxx-jyy)
        var axis=Math.toDegrees(gradAngle + Math.PI/2).toFloat()
        while(axis<0) axis+=180f
        while(axis>=180f) axis-=180f
        return GrainReport(
            axisDegrees=axis,
            confidence=coherence.toFloat(),
            note="芝目の『軸』の推定です。順目/逆目の向きまでは単眼画像だけでは安定判定できません。"
        )
    }
}
