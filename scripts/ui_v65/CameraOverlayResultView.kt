package jp.example.greenreader.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BlurMaskFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PathMeasure
import android.graphics.PointF
import android.graphics.RectF
import android.graphics.Typeface
import android.os.SystemClock
import android.view.View
import jp.example.greenreader.analysis.PuttAdvisor
import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Captured camera frame + futuristic putting HUD.
 * The predicted roll path carries animated chevrons toward the cup.
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
    private var positiveCrossScreen: PointF? = null

    private val bitmapPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val dimPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(58, 0, 24, 17)
        style = Paint.Style.FILL
    }
    private val rollGlow = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(105, 0, 255, 190)
        strokeWidth = 12f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
        maskFilter = BlurMaskFilter(13f, BlurMaskFilter.Blur.NORMAL)
    }
    private val rollPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(225, 255, 248)
        strokeWidth = 2.8f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val aimPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(245, 235, 92)
        strokeWidth = 3.5f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        pathEffect = DashPathEffect(floatArrayOf(18f, 14f), 0f)
        setShadowLayer(10f, 0f, 0f, Color.rgb(255, 230, 70))
    }
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val slopePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(70, 255, 214)
        strokeWidth = 5f
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val hudPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = Color.argb(210, 70, 255, 205)
        strokeWidth = 2.5f
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(220, 255, 245)
        textSize = 30f
        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
    }

    init {
        setLayerType(LAYER_TYPE_SOFTWARE, null)
    }

    fun setResult(
        bitmap: Bitmap,
        ball: PointF,
        cup: PointF,
        slopeReport: SlopeReport,
        puttAdvice: PuttAdvisor.Advice,
        positiveCrossDirection: PointF? = null
    ) {
        frameBitmap = bitmap
        ballPoint = PointF(ball.x, ball.y)
        cupPoint = PointF(cup.x, cup.y)
        report = slopeReport
        advice = puttAdvice
        positiveCrossScreen = positiveCrossDirection?.let { PointF(it.x, it.y) }
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
        positiveCrossScreen = null
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)

        val bitmap = frameBitmap ?: run {
            textPaint.textAlign = Paint.Align.CENTER
            textPaint.setShadowLayer(12f, 0f, 0f, Color.rgb(0, 255, 190))
            canvas.drawText("GREEN READER // AR RESULT", width / 2f, height / 2f, textPaint)
            textPaint.clearShadowLayer()
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
        val imageRect = RectF(left, top, left + drawnW, top + drawnH)
        canvas.drawBitmap(bitmap, null, imageRect, bitmapPaint)
        canvas.drawRect(imageRect, dimPaint)

        fun mapPoint(p: PointF) = PointF(left + p.x * scale, top + p.y * scale)
        val b = mapPoint(ball)
        val c = mapPoint(cup)
        val dx = c.x - b.x
        val dy = c.y - b.y
        val screenDistance = hypot(dx.toDouble(), dy.toDouble()).toFloat().coerceAtLeast(1f)
        val ux = dx / screenDistance
        val uy = dy / screenDistance
        val projectedCross = positiveCrossScreen
        val nx = projectedCross?.x ?: uy
        val ny = projectedCross?.y ?: -ux

        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val aimPx = ((a.aimOffsetCm / 100f) * pxPerMeter)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)
        val aim = PointF(c.x + nx * aimPx, c.y + ny * aimPx)

        canvas.drawLine(b.x, b.y, aim.x, aim.y, aimPaint)

        val rollPath = PrecisionRollPath.build(
            startX = b.x,
            startY = b.y,
            endX = c.x,
            endY = c.y,
            crossX = nx,
            crossY = ny,
            report = r,
            aimOffsetPx = aimPx
        )
        canvas.drawPath(rollPath, rollGlow)

        // Fine dual-core line: a translucent mid layer and a crisp sub-3 px core.
        rollPaint.strokeWidth = 5.2f
        rollPaint.color = Color.argb(120, 90, 255, 216)
        canvas.drawPath(rollPath, rollPaint)
        rollPaint.strokeWidth = 2.4f
        rollPaint.color = Color.rgb(232, 255, 249)
        canvas.drawPath(rollPath, rollPaint)

        drawAdaptiveChevrons(canvas, rollPath)

        drawMarker(canvas, b, Color.rgb(225, 255, 248), 17f)
        drawMarker(canvas, c, Color.rgb(70, 255, 190), 22f)
        drawMarker(canvas, aim, Color.rgb(255, 226, 88), 13f)

        drawLabels(canvas, b, c, aim)
        drawSlopeVectors(canvas, b, c, r)
        drawHudFrame(canvas, imageRect)
        drawInfoPanel(canvas, imageRect, r, a)

        postInvalidateOnAnimation()
    }

    private fun drawMarker(canvas: Canvas, p: PointF, color: Int, radius: Float) {
        markerPaint.color = color
        markerPaint.setShadowLayer(18f, 0f, 0f, color)
        canvas.drawCircle(p.x, p.y, radius, markerPaint)
        markerPaint.clearShadowLayer()
        markerPaint.color = Color.rgb(1, 20, 14)
        canvas.drawCircle(p.x, p.y, radius * 0.38f, markerPaint)
    }

    private fun drawLabels(canvas: Canvas, b: PointF, c: PointF, aim: PointF) {
        textPaint.textAlign = Paint.Align.LEFT
        textPaint.textSize = 20f
        textPaint.color = Color.rgb(205, 255, 242)
        canvas.drawText("BALL", b.x + 22f, b.y - 14f, textPaint)
        canvas.drawText("CUP", c.x + 24f, c.y - 15f, textPaint)
        textPaint.color = Color.rgb(255, 235, 110)
        canvas.drawText("AIM", aim.x + 18f, aim.y + 7f, textPaint)
    }

    private fun drawSlopeVectors(canvas: Canvas, b: PointF, c: PointF, r: SlopeReport) {
        val dx = c.x - b.x
        val dy = c.y - b.y
        val d = hypot(dx.toDouble(), dy.toDouble()).toFloat().coerceAtLeast(1f)
        val ux = dx / d
        val uy = dy / d
        val projectedCross = positiveCrossScreen
        val nx = projectedCross?.x ?: uy
        val ny = projectedCross?.y ?: -ux
        val phase = (SystemClock.uptimeMillis() % 1200L) / 1200f
        val pulse = 0.55f + 0.45f * kotlin.math.sin(phase * Math.PI.toFloat() * 2f)

        r.segments.forEachIndexed { i, seg ->
            val t = (i + 0.5f) / r.segments.size.coerceAtLeast(1)
            val x = b.x + dx * t
            val y = b.y + dy * t
            val downhillSign = if (seg.crossPercent >= 0f) -1f else 1f
            val arrowLen = (25f + abs(seg.crossPercent) * 9f).coerceIn(25f, 78f)
            val ex = x + nx * arrowLen * downhillSign
            val ey = y + ny * arrowLen * downhillSign
            slopePaint.strokeWidth = 3.5f + pulse * 2f
            slopePaint.color = Color.argb((145 + pulse * 110).toInt(), 65, 255, 215)
            slopePaint.setShadowLayer(8f + pulse * 7f, 0f, 0f, Color.rgb(0, 255, 190))
            canvas.drawLine(x, y, ex, ey, slopePaint)
            val head = 10f
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
            slopePaint.clearShadowLayer()
        }
    }

    private fun drawAdaptiveChevrons(canvas: Canvas, path: Path) {
        val measure = PathMeasure(path, false)
        val length = measure.length
        if (length <= 1f) return

        // Move by a fraction of one local spacing rather than shifting the whole
        // distribution, so arrows flow continuously without bunching.
        val phase = (SystemClock.uptimeMillis() % 1300L) / 1300f
        var d = phase * 28f
        val pos = FloatArray(2)
        val tan = FloatArray(2)
        val tanA = FloatArray(2)
        val tanB = FloatArray(2)

        while (d < length) {
            if (!measure.getPosTan(d, pos, tan)) {
                d += 28f
                continue
            }

            val sample = min(10f, max(4f, length * 0.012f))
            measure.getPosTan((d - sample).coerceAtLeast(0f), null, tanA)
            measure.getPosTan((d + sample).coerceAtMost(length), null, tanB)

            fun normalize(v: FloatArray): Pair<Float, Float> {
                val m = sqrt(v[0] * v[0] + v[1] * v[1]).coerceAtLeast(0.001f)
                return Pair(v[0] / m, v[1] / m)
            }

            val (ax, ay) = normalize(tanA)
            val (bx, by) = normalize(tanB)
            val dot = (ax * bx + ay * by).coerceIn(-1f, 1f)
            val turn = (acos(dot) / 0.55f).coerceIn(0f, 1f)

            val mag = sqrt(tan[0] * tan[0] + tan[1] * tan[1]).coerceAtLeast(0.001f)
            val ux = tan[0] / mag
            val uy = tan[1] / mag
            val nx = -uy
            val ny = ux

            // Tight curvature => smaller, thinner and denser arrows.
            val arrowLength = 11f - turn * 4.5f
            val halfWidth = 7f - turn * 3.2f
            val stroke = 2.8f - turn * 0.9f
            val spacing = 38f - turn * 17f

            val backX = pos[0] - ux * arrowLength
            val backY = pos[1] - uy * arrowLength

            hudPaint.style = Paint.Style.STROKE
            hudPaint.strokeWidth = stroke
            hudPaint.strokeCap = Paint.Cap.ROUND
            hudPaint.color = Color.argb(238, 225, 255, 248)
            hudPaint.setShadowLayer(7f - turn * 2f, 0f, 0f, Color.rgb(0, 255, 190))
            canvas.drawLine(backX + nx * halfWidth, backY + ny * halfWidth, pos[0], pos[1], hudPaint)
            canvas.drawLine(backX - nx * halfWidth, backY - ny * halfWidth, pos[0], pos[1], hudPaint)
            hudPaint.clearShadowLayer()

            d += spacing
        }
    }

    private fun drawHudFrame(canvas: Canvas, rect: RectF) {
        val inset = 14f
        val l = rect.left + inset
        val t = rect.top + inset
        val r = rect.right - inset
        val b = rect.bottom - inset
        val c = 34f
        hudPaint.strokeWidth = 2.5f
        hudPaint.color = Color.argb(200, 80, 255, 210)
        hudPaint.setShadowLayer(12f, 0f, 0f, Color.rgb(0, 255, 190))
        canvas.drawLine(l, t + c, l, t, hudPaint)
        canvas.drawLine(l, t, l + c, t, hudPaint)
        canvas.drawLine(r - c, t, r, t, hudPaint)
        canvas.drawLine(r, t, r, t + c, hudPaint)
        canvas.drawLine(l, b - c, l, b, hudPaint)
        canvas.drawLine(l, b, l + c, b, hudPaint)
        canvas.drawLine(r - c, b, r, b, hudPaint)
        canvas.drawLine(r, b - c, r, b, hudPaint)
        hudPaint.clearShadowLayer()
    }

    private fun drawInfoPanel(
        canvas: Canvas,
        rect: RectF,
        r: SlopeReport,
        a: PuttAdvisor.Advice
    ) {
        val boxW = (width * 0.34f).coerceAtMost(420f)
        val boxH = 128f
        val box = RectF(
            rect.left + 26f,
            rect.top + 30f,
            rect.left + 26f + boxW,
            rect.top + 30f + boxH
        )
        markerPaint.style = Paint.Style.FILL
        markerPaint.color = Color.argb(178, 0, 18, 13)
        canvas.drawRoundRect(box, 18f, 18f, markerPaint)

        hudPaint.style = Paint.Style.STROKE
        hudPaint.strokeWidth = 2f
        hudPaint.color = Color.argb(210, 60, 255, 200)
        canvas.drawRoundRect(box, 18f, 18f, hudPaint)

        textPaint.textAlign = Paint.Align.LEFT
        textPaint.typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
        textPaint.color = Color.rgb(110, 255, 211)
        textPaint.textSize = 18f
        canvas.drawText("GREEN READER // RESULT", box.left + 16f, box.top + 26f, textPaint)

        textPaint.color = Color.rgb(225, 255, 247)
        textPaint.textSize = 20f
        canvas.drawText(
            String.format("DIST %.2fm   LONG %+.1f%%", r.distanceMeters, r.overallLongitudinalPercent),
            box.left + 16f, box.top + 60f, textPaint
        )
        canvas.drawText(
            String.format("CROSS %+.1f%%   AIM %.0fcm", r.overallCrossPercent, abs(a.aimOffsetCm)),
            box.left + 16f, box.top + 92f, textPaint
        )
    }
}
