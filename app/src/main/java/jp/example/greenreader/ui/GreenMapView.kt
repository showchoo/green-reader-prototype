package jp.example.greenreader.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.view.View
import jp.example.greenreader.analysis.GrainReport
import jp.example.greenreader.analysis.PuttAdvisor
import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * Top-down visualization for the measured putt corridor.
 * This is deliberately a visualization of measured/estimated slope segments,
 * not a claim that the entire green has been reconstructed yet.
 */
class GreenMapView(context: Context) : View(context) {
    var report: SlopeReport? = null
        set(value) { field = value; invalidate() }
    var advice: PuttAdvisor.Advice? = null
        set(value) { field = value; invalidate() }
    var grain: GrainReport? = null
        set(value) { field = value; invalidate() }

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 30f
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.rgb(18, 44, 28))

        val r = report
        if (r == null) {
            textPaint.textAlign = Paint.Align.CENTER
            textPaint.textSize = 34f
            canvas.drawText("解析後にここへグリーンマップを表示", width / 2f, height / 2f, textPaint)
            textPaint.textSize = 24f
            canvas.drawText("色＝高低傾向　矢印＝傾斜方向　白線＝推奨ライン", width / 2f, height / 2f + 46f, textPaint)
            return
        }

        val left = width * 0.14f
        val right = width * 0.86f
        val top = height * 0.08f
        val bottom = height * 0.88f
        val corridorW = right - left
        val corridorH = bottom - top

        paint.style = Paint.Style.FILL
        paint.color = Color.rgb(30, 92, 45)
        canvas.drawRoundRect(left, top, right, bottom, 32f, 32f, paint)

        val segments = r.segments
        if (segments.isNotEmpty()) {
            val maxSlope = max(3f, segments.maxOf { max(abs(it.longitudinalPercent), abs(it.crossPercent)) })
            segments.forEachIndexed { i, s ->
                val y1 = bottom - corridorH * (i + 1f) / segments.size
                val y2 = bottom - corridorH * i / segments.size
                paint.color = heatColor(s.longitudinalPercent / maxSlope)
                canvas.drawRect(left + 4f, y1, right - 4f, y2, paint)

                val cx = (left + right) / 2f
                val cy = (y1 + y2) / 2f
                drawSlopeArrow(canvas, cx, cy, s.crossPercent, s.longitudinalPercent)
            }
        }

        // Suggested putt line. Positive aim offset means left in the advisor.
        val adv = advice
        val startX = (left + right) / 2f
        val startY = bottom - 28f
        val endX = (left + right) / 2f
        val endY = top + 28f
        val path = Path().apply {
            moveTo(startX, startY)
            if (adv != null) {
                val halfWidthM = 0.65f
                val pxPerM = (corridorW / 2f) / halfWidthM
                val offsetPx = (adv.aimOffsetCm / 100f * pxPerM).coerceIn(-corridorW * 0.35f, corridorW * 0.35f)
                cubicTo(startX + offsetPx * 0.45f, startY - corridorH * 0.25f,
                    endX + offsetPx, top + corridorH * 0.35f,
                    endX, endY)
            } else {
                lineTo(endX, endY)
            }
        }
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 8f
        paint.color = Color.WHITE
        canvas.drawPath(path, paint)

        // Ball / cup markers.
        paint.style = Paint.Style.FILL
        paint.color = Color.WHITE
        canvas.drawCircle(startX, startY, 15f, paint)
        paint.color = Color.BLACK
        canvas.drawCircle(endX, endY, 19f, paint)
        paint.color = Color.WHITE
        canvas.drawCircle(endX, endY, 11f, paint)

        textPaint.textAlign = Paint.Align.LEFT
        textPaint.textSize = 25f
        val advText = advice?.let {
            val side = if (it.aimOffsetCm >= 0f) "左" else "右"
            "推奨: ${side}${abs(it.aimOffsetCm).toInt()}cm / 実質 %.2fm".format(it.effectiveDistanceM)
        } ?: "推奨ライン: 未計算"
        canvas.drawText("距離 %.2fm  縦 %.1f%%  横 %.1f%%".format(r.distanceMeters, r.overallLongitudinalPercent, r.overallCrossPercent), 18f, height - 58f, textPaint)
        canvas.drawText(advText, 18f, height - 24f, textPaint)

        grain?.let { g ->
            textPaint.textAlign = Paint.Align.RIGHT
            canvas.drawText("芝目軸 %.0f°  信頼度 %.0f%%".format(g.axisDegrees, g.confidence * 100f), width - 18f, 34f, textPaint)
        }
    }

    private fun heatColor(v: Float): Int {
        val x = v.coerceIn(-1f, 1f)
        return if (x >= 0f) {
            val t = x
            Color.rgb((55 + 175 * t).toInt(), (145 - 75 * t).toInt(), (70 - 25 * t).toInt())
        } else {
            val t = -x
            Color.rgb((45 - 15 * t).toInt(), (135 - 45 * t).toInt(), (85 + 155 * t).toInt())
        }
    }

    private fun drawSlopeArrow(canvas: Canvas, cx: Float, cy: Float, cross: Float, longitudinal: Float) {
        val mag = max(0.001f, kotlin.math.sqrt(cross * cross + longitudinal * longitudinal))
        val dx = (cross / mag) * 32f
        val dy = -(longitudinal / mag) * 32f
        val ex = cx + dx
        val ey = cy + dy

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 5f
        paint.color = Color.argb(220, 255, 255, 255)
        canvas.drawLine(cx - dx * 0.35f, cy - dy * 0.35f, ex, ey, paint)

        val a = atan2(dy, dx)
        val head = 12f
        val a1 = a + 2.55f
        val a2 = a - 2.55f
        canvas.drawLine(ex, ey, ex + cos(a1) * head, ey + sin(a1) * head, paint)
        canvas.drawLine(ex, ey, ex + cos(a2) * head, ey + sin(a2) * head, paint)
    }
}
