package jp.example.greenreader.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PointF
import android.graphics.RectF
import android.graphics.Typeface
import android.view.View
import jp.example.greenreader.analysis.PuttAdvisor
import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.abs
import kotlin.math.hypot

/**
 * Captured camera frame + calculated putting overlay.
 *
 * v0.7 visual semantics:
 * - cyan arrows = DOWNHILL direction (where gravity pulls the ball)
 * - yellow dashed line = AIM guide toward the uphill-side aim point
 * - solid white curve = predicted roll path bending back downhill toward the cup
 */
class CameraOverlayResultView(context: Context) : View(context) {
    var frameBitmap: Bitmap? = null
        private set
    var ballPoint: PointF? = null
        private set
    var cupPoint: PointF? = null
        private set
    var report: SlopeReport? = null
        private set
    var advice: PuttAdvisor.Advice? = null
        private set

    private val bitmapPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val rollPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        strokeWidth = 10f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
        setShadowLayer(7f, 0f, 2f, Color.BLACK)
    }
    private val aimPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.YELLOW
        strokeWidth = 5f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        pathEffect = DashPathEffect(floatArrayOf(18f, 14f), 0f)
        setShadowLayer(4f, 0f, 1f, Color.BLACK)
    }
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        setShadowLayer(5f, 0f, 2f, Color.BLACK)
    }
    private val slopePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.CYAN
        strokeWidth = 6f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        setShadowLayer(4f, 0f, 1f, Color.BLACK)
    }
    private val chipPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(205, 5, 18, 13)
        style = Paint.Style.FILL
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 34f
        typeface = Typeface.DEFAULT_BOLD
        setShadowLayer(6f, 0f, 2f, Color.BLACK)
    }
    private val smallText = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(206, 232, 216)
        textSize = 25f
        typeface = Typeface.DEFAULT_BOLD
        setShadowLayer(4f, 0f, 1f, Color.BLACK)
    }

    init {
        setLayerType(LAYER_TYPE_SOFTWARE, null)
    }

    fun setResult(
        bitmap: Bitmap,
        ball: PointF,
        cup: PointF,
        slopeReport: SlopeReport,
        puttAdvice: PuttAdvisor.Advice
    ) {
        frameBitmap = bitmap
        ballPoint = PointF(ball.x, ball.y)
        cupPoint = PointF(cup.x, cup.y)
        report = slopeReport
        advice = puttAdvice
        invalidate()
    }

    fun updateAdvice(puttAdvice: PuttAdvisor.Advice) {
        advice = puttAdvice
        invalidate()
    }

    fun clear() {
        frameBitmap = null
        ballPoint = null
        cupPoint = null
        report = null
        advice = null
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)

        val bitmap = frameBitmap ?: run {
            textPaint.textAlign = Paint.Align.CENTER
            canvas.drawText("解析後に実画像上へラインを表示", width / 2f, height / 2f, textPaint)
            return
        }
        val ball = ballPoint ?: return
        val cup = cupPoint ?: return
        val r = report ?: return
        val a = advice ?: return

        val scale = minOf(width.toFloat() / bitmap.width, height.toFloat() / bitmap.height)
        val drawnW = bitmap.width * scale
        val drawnH = bitmap.height * scale
        val left = (width - drawnW) / 2f
        val top = (height - drawnH) / 2f
        canvas.drawBitmap(bitmap, null, RectF(left, top, left + drawnW, top + drawnH), bitmapPaint)

        fun mapPoint(p: PointF) = PointF(left + p.x * scale, top + p.y * scale)
        val b = mapPoint(ball)
        val c = mapPoint(cup)
        val dx = c.x - b.x
        val dy = c.y - b.y
        val screenDistance = hypot(dx.toDouble(), dy.toDouble()).toFloat().coerceAtLeast(1f)
        val ux = dx / screenDistance
        val uy = dy / screenDistance
        // Screen-space LEFT normal for BALL -> CUP.
        val nx = uy
        val ny = -ux

        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val aimPx = ((a.aimOffsetCm / 100f) * pxPerMeter)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)

        // Aim point is deliberately UPHILL. The solid roll path starts toward this
        // point and then bends DOWNHILL back into the cup.
        val aim = PointF(c.x + nx * aimPx, c.y + ny * aimPx)
        canvas.drawLine(b.x, b.y, aim.x, aim.y, aimPaint)

        val control1 = PointF(
            b.x + (aim.x - b.x) * 0.45f,
            b.y + (aim.y - b.y) * 0.45f
        )
        val control2 = PointF(
            c.x + nx * aimPx * 0.55f,
            c.y + ny * aimPx * 0.55f
        )
        val rollPath = Path().apply {
            moveTo(b.x, b.y)
            cubicTo(control1.x, control1.y, control2.x, control2.y, c.x, c.y)
        }
        canvas.drawPath(rollPath, rollPaint)

        // Ball / cup / aim markers.
        markerPaint.color = Color.WHITE
        canvas.drawCircle(b.x, b.y, 19f, markerPaint)
        markerPaint.color = Color.RED
        canvas.drawCircle(c.x, c.y, 22f, markerPaint)
        markerPaint.color = Color.YELLOW
        canvas.drawCircle(aim.x, aim.y, 17f, markerPaint)

        textPaint.textAlign = Paint.Align.LEFT
        textPaint.textSize = 28f
        canvas.drawText("BALL", b.x + 24f, b.y - 16f, textPaint)
        canvas.drawText("CUP", c.x + 26f, c.y - 16f, textPaint)
        canvas.drawText("狙い点", aim.x + 22f, aim.y + 8f, textPaint)

        // Cyan arrows now show DOWNHILL (opposite the height gradient).
        r.segments.forEachIndexed { i, seg ->
            val t = (i + 0.5f) / r.segments.size
            val x = b.x + dx * t
            val y = b.y + dy * t
            val downhillSign = if (seg.crossPercent >= 0f) -1f else 1f
            val arrowLen = (28f + abs(seg.crossPercent) * 12f).coerceIn(28f, 90f)
            val ex = x + nx * arrowLen * downhillSign
            val ey = y + ny * arrowLen * downhillSign
            canvas.drawLine(x, y, ex, ey, slopePaint)
            val head = 11f
            canvas.drawLine(
                ex, ey,
                ex - nx * head * downhillSign - ux * head,
                ey - ny * head * downhillSign - uy * head,
                slopePaint
            )
            canvas.drawLine(
                ex, ey,
                ex - nx * head * downhillSign + ux * head,
                ey - ny * head * downhillSign + uy * head,
                slopePaint
            )
        }

        // Compact HUD summary.
        val chipTop = height - 106f
        canvas.drawRoundRect(12f, chipTop, width - 12f, height - 12f, 22f, 22f, chipPaint)
        val side = if (a.aimOffsetCm >= 0f) "左" else "右"
        textPaint.textSize = 31f
        canvas.drawText("狙い ${side}${abs(a.aimOffsetCm).toInt()}cm", 28f, height - 62f, textPaint)
        smallText.textAlign = Paint.Align.LEFT
        canvas.drawText(
            String.format("白=予測転がり  黄点線=狙い  水色=下り  %.2fm / 横 %.1f%%", r.distanceMeters, r.overallCrossPercent),
            28f,
            height - 28f,
            smallText
        )
    }
}
