package jp.example.greenreader.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View
import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.abs
import kotlin.math.max

class ProfileView @JvmOverloads constructor(c: Context, a: AttributeSet?=null): View(c,a) {
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply { strokeWidth=4f; style=Paint.Style.STROKE }
    private val fill=Paint(Paint.ANTI_ALIAS_FLAG).apply { style=Paint.Style.FILL }
    var report:SlopeReport?=null
        set(v){ field=v; invalidate() }

    override fun onDraw(canvas:Canvas){
        super.onDraw(canvas)
        val r=report ?: run {
            fill.textSize=36f; canvas.drawText("スキャン後に傾斜プロファイルを表示",24f,height/2f,fill); return
        }
        val pad=40f; val w=width-2*pad; val h=height-2*pad
        val elevs=r.segments.map{it.elevationMeters}
        val min=elevs.minOrNull()?:0f; val max=elevs.maxOrNull()?:0f
        val range=max(0.02f,max-min)
        val path=Path()
        r.segments.forEachIndexed { i,s ->
            val x=pad+w*(i+0.5f)/r.segments.size
            val y=pad+h*(1f-(s.elevationMeters-min)/range)
            if(i==0) path.moveTo(x,y) else path.lineTo(x,y)
        }
        canvas.drawPath(path,paint)
        fill.textSize=28f
        canvas.drawText("0m",pad,height-8f,fill)
        canvas.drawText(String.format("%.1fm",r.distanceMeters),width-pad-90f,height-8f,fill)
        r.segments.forEachIndexed{i,s->
            if(i%2==0){
                val x=pad+w*(i+0.5f)/r.segments.size
                val side=if(s.crossPercent>0)"←" else "→"
                canvas.drawText("$side${String.format("%.1f",abs(s.crossPercent))}%",x-38f,pad+30f,fill)
            }
        }
    }
}
