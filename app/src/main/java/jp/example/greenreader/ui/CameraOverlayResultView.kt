package jp.example.greenreader.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
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
 * The image is the same GL frame used to project the ball/cup world positions.
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
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        strokeWidth = 10f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
        setShadowLayer(7f, 0f, 2f, Color.BLACK)
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
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 34f
        typeface = Typeface.DEFAULT_BOLD
        setShadowLayer(6f, 0f, 2f, Color.BLACK)
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
        // Screen-space left normal for ball -> cup.
        val nx = uy
        val ny = -ux

        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val aimPx = ((a.aimOffsetCm / 100f) * pxPerMeter)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)

        val aim = PointF(c.x + nx * aimPx, c.y + ny * aimPx)
        val controlX = (b.x + c.x) * 0.5f + nx * aimPx * 0.95f
        val controlY = (b.y + c.y) * 0.5f + ny * aimPx * 0.95f
        val path = Path().apply {
            moveTo(b.x, b.y)
            quadTo(controlX, controlY, c.x, c.y)
        }
        canvas.drawPath(path, linePaint)

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

        r.segments.forEachIndexed { i, seg ->
            val t = (i + 0.5f) / r.segments.size
            val x = b.x + dx * t
            val y = b.y + dy * t
            val sign = if (seg.crossPercent >= 0f) 1f else -1f
            val arrowLen = (28f + abs(seg.crossPercent) * 12f).coerceIn(28f, 90f)
            val ex = x + nx * arrowLen * sign
            val ey = y + ny * arrowLen * sign
            canvas.drawLine(x, y, ex, ey, slopePaint)
            val head = 11f
            canvas.drawLine(ex, ey, ex - nx * head * sign - ux * head, ey - ny * head * sign - uy * head, slopePaint)
            canvas.drawLine(ex, ey, ex - nx * head * sign + ux * head, ey - ny * head * sign + uy * head, slopePaint)
        }

        textPaint.textSize = 32f
        val side = if (a.aimOffsetCm >= 0f) "左" else "右"
        val summary = String.format(
            "%s %.0fcm狙い / %.2fm / 縦 %.1f%% 横 %.1f%%",
            side,
            abs(a.aimOffsetCm),
            r.distanceMeters,
            r.overallLongitudinalPercent,
            r.overallCrossPercent
        )
        canvas.drawText(summary, 20f, height - 28f, textPaint)
    }
}
