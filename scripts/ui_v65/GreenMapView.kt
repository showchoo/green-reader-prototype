package jp.example.greenreader.ui

import android.content.Context
import android.graphics.BlurMaskFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Shader
import android.os.SystemClock
import android.view.View
import jp.example.greenreader.analysis.GrainReport
import jp.example.greenreader.analysis.PuttAdvisor
import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Futuristic top-down visualization for the measured putt corridor.
 * Animated neon chevrons indicate downhill flow while the bright curve
 * shows the predicted roll path.
 */
class GreenMapView(context: Context) : View(context) {
    var report: SlopeReport? = null
        set(value) { field = value; invalidate() }
    var advice: PuttAdvisor.Advice? = null
        set(value) { field = value; invalidate() }
    var grain: GrainReport? = null
        set(value) { field = value; invalidate() }

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val glow = Paint(Paint.ANTI_ALIAS_FLAG)
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(213, 255, 241)
        textSize = 30f
    }

    init {
        setLayerType(LAYER_TYPE_SOFTWARE, null)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        drawBackground(canvas)

        val r = report
        if (r == null) {
            textPaint.textAlign = Paint.Align.CENTER
            textPaint.textSize = 34f
            textPaint.setShadowLayer(12f, 0f, 0f, Color.rgb(0, 255, 190))
            canvas.drawText("GREEN READER // MAP", width / 2f, height / 2f - 18f, textPaint)
            textPaint.clearShadowLayer()
            textPaint.textSize = 22f
            canvas.drawText("解析後にネオン傾斜マップを表示", width / 2f, height / 2f + 30f, textPaint)
            return
        }

        val left = width * 0.10f
        val right = width * 0.90f
        val top = height * 0.08f
        val bottom = height * 0.88f
        val corridorW = right - left
        val corridorH = bottom - top

        paint.style = Paint.Style.FILL
        paint.shader = LinearGradient(
            left, top, right, bottom,
            intArrayOf(
                Color.argb(190, 2, 30, 22),
                Color.argb(210, 0, 48, 34),
                Color.argb(220, 2, 22, 18)
            ),
            null,
            Shader.TileMode.CLAMP
        )
        canvas.drawRoundRect(left, top, right, bottom, 34f, 34f, paint)
        paint.shader = null

        drawHudFrame(canvas, left, top, right, bottom)
        drawCorridorGrid(canvas, left, top, right, bottom)

        val segments = r.segments
        if (segments.isNotEmpty()) {
            val maxSlope = max(3f, segments.maxOf { max(abs(it.longitudinalPercent), abs(it.crossPercent)) })
            segments.forEachIndexed { i, s ->
                val y1 = bottom - corridorH * (i + 1f) / segments.size
                val y2 = bottom - corridorH * i / segments.size
                paint.style = Paint.Style.FILL
                paint.color = heatColor(s.longitudinalPercent / maxSlope)
                canvas.drawRect(left + 5f, y1, right - 5f, y2, paint)

                val cx = (left + right) / 2f
                val cy = (y1 + y2) / 2f
                drawAnimatedDownhillArrow(canvas, cx, cy, s.crossPercent, s.longitudinalPercent, i)
            }
        }

        val adv = advice
        val startX = (left + right) / 2f
        val startY = bottom - 30f
        val endX = (left + right) / 2f
        val endY = top + 30f
        val halfWidthM = 0.65f
        val pxPerM = (corridorW / 2f) / halfWidthM
        val offsetPx = ((adv?.aimOffsetCm ?: 0f) / 100f * pxPerM)
            .coerceIn(-corridorW * 0.35f, corridorW * 0.35f)

        val path = PrecisionRollPath.build(
            startX = startX,
            startY = startY,
            endX = endX,
            endY = endY,
            crossX = 1f,
            crossY = 0f,
            report = r,
            aimOffsetPx = offsetPx
        )

        glow.style = Paint.Style.STROKE
        glow.strokeWidth = 11f
        glow.strokeCap = Paint.Cap.ROUND
        glow.strokeJoin = Paint.Join.ROUND
        glow.color = Color.argb(95, 0, 255, 190)
        glow.maskFilter = BlurMaskFilter(13f, BlurMaskFilter.Blur.NORMAL)
        canvas.drawPath(path, glow)
        glow.maskFilter = null

        paint.style = Paint.Style.STROKE
        paint.strokeCap = Paint.Cap.ROUND
        paint.strokeJoin = Paint.Join.ROUND
        paint.strokeWidth = 5f
        paint.color = Color.argb(115, 80, 255, 213)
        canvas.drawPath(path, paint)
        paint.strokeWidth = 2.3f
        paint.color = Color.rgb(224, 255, 247)
        canvas.drawPath(path, paint)

        drawAdaptiveFlowChevrons(canvas, path)

        paint.style = Paint.Style.FILL
        paint.color = Color.rgb(220, 255, 246)
        paint.setShadowLayer(18f, 0f, 0f, Color.rgb(0, 255, 190))
        canvas.drawCircle(startX, startY, 14f, paint)
        paint.color = Color.rgb(96, 255, 190)
        canvas.drawCircle(endX, endY, 20f, paint)
        paint.color = Color.rgb(5, 20, 16)
        canvas.drawCircle(endX, endY, 9f, paint)
        paint.clearShadowLayer()

        textPaint.textAlign = Paint.Align.LEFT
        textPaint.textSize = 18f
        textPaint.color = Color.rgb(150, 255, 220)
        canvas.drawText(
            String.format("LONG %+.1f%%   CROSS %+.1f%%   %.2fm",
                r.overallLongitudinalPercent,
                r.overallCrossPercent,
                r.distanceMeters),
            left + 18f, top + 30f, textPaint
        )

        textPaint.textAlign = Paint.Align.CENTER
        textPaint.textSize = 20f
        textPaint.color = Color.rgb(195, 255, 236)
        canvas.drawText("FLOW VECTOR  //  PREDICTED ROLL", width / 2f, height - 28f, textPaint)

        if (grain != null) {
            textPaint.textAlign = Paint.Align.RIGHT
            textPaint.textSize = 18f
            textPaint.color = Color.rgb(117, 255, 190)
            canvas.drawText("GRAIN DATA // LOCKED", width - 18f, 34f, textPaint)
        }

        postInvalidateOnAnimation()
    }

    private fun drawBackground(canvas: Canvas) {
        canvas.drawColor(Color.rgb(2, 10, 8))
        val spacing = max(42f, width / 12f)
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1f
        paint.color = Color.argb(42, 0, 255, 170)
        var x = 0f
        while (x <= width) {
            canvas.drawLine(x, 0f, x, height.toFloat(), paint)
            x += spacing
        }
        var y = 0f
        while (y <= height) {
            canvas.drawLine(0f, y, width.toFloat(), y, paint)
            y += spacing
        }
    }

    private fun drawHudFrame(canvas: Canvas, l: Float, t: Float, r: Float, b: Float) {
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 3f
        paint.color = Color.argb(220, 54, 255, 198)
        paint.setShadowLayer(14f, 0f, 0f, Color.rgb(0, 255, 190))
        canvas.drawRoundRect(l, t, r, b, 34f, 34f, paint)
        paint.clearShadowLayer()

        val c = 26f
        paint.strokeWidth = 5f
        canvas.drawLine(l, t + c, l, t, paint)
        canvas.drawLine(l, t, l + c, t, paint)
        canvas.drawLine(r - c, t, r, t, paint)
        canvas.drawLine(r, t, r, t + c, paint)
        canvas.drawLine(l, b - c, l, b, paint)
        canvas.drawLine(l, b, l + c, b, paint)
        canvas.drawLine(r - c, b, r, b, paint)
        canvas.drawLine(r, b - c, r, b, paint)
    }

    private fun drawCorridorGrid(canvas: Canvas, l: Float, t: Float, r: Float, b: Float) {
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.2f
        paint.color = Color.argb(70, 77, 255, 210)
        for (i in 1 until 8) {
            val y = t + (b - t) * i / 8f
            canvas.drawLine(l, y, r, y, paint)
        }
        for (i in 1 until 6) {
            val x = l + (r - l) * i / 6f
            canvas.drawLine(x, t, x, b, paint)
        }
    }

    private fun heatColor(v: Float): Int {
        val x = v.coerceIn(-1f, 1f)
        return if (x >= 0f) {
            val t = x
            Color.argb(100, (35 + 130 * t).toInt(), (205 + 45 * t).toInt(), (115 - 45 * t).toInt())
        } else {
            val t = -x
            Color.argb(100, (20 - 5 * t).toInt(), (155 + 65 * t).toInt(), (135 + 110 * t).toInt())
        }
    }

    private fun drawAnimatedDownhillArrow(
        canvas: Canvas,
        cx: Float,
        cy: Float,
        cross: Float,
        longitudinal: Float,
        index: Int
    ) {
        val mag = max(0.001f, sqrt(cross * cross + longitudinal * longitudinal))
        val dx = -(cross / mag) * 34f
        val dy = (longitudinal / mag) * 34f
        val phase = ((SystemClock.uptimeMillis() / 18L + index * 17L) % 100L) / 100f
        val pulse = 0.55f + 0.45f * sin(phase * Math.PI.toFloat() * 2f)
        val ex = cx + dx
        val ey = cy + dy

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 4.5f + pulse * 2f
        paint.strokeCap = Paint.Cap.ROUND
        paint.color = Color.argb((150 + pulse * 105).toInt(), 80, 255, 220)
        paint.setShadowLayer(10f + pulse * 8f, 0f, 0f, Color.rgb(0, 255, 190))
        canvas.drawLine(cx - dx * 0.28f, cy - dy * 0.28f, ex, ey, paint)

        val a = atan2(dy, dx)
        val head = 13f
        val a1 = a + 2.55f
        val a2 = a - 2.55f
        canvas.drawLine(ex, ey, ex + cos(a1) * head, ey + sin(a1) * head, paint)
        canvas.drawLine(ex, ey, ex + cos(a2) * head, ey + sin(a2) * head, paint)
        paint.clearShadowLayer()
    }

    private fun drawAdaptiveFlowChevrons(canvas: Canvas, path: Path) {
        val measure = android.graphics.PathMeasure(path, false)
        val length = measure.length
        if (length <= 1f) return

        val phase = (SystemClock.uptimeMillis() % 1350L) / 1350f
        var d = phase * 26f
        val pos = FloatArray(2)
        val tan = FloatArray(2)
        val tanA = FloatArray(2)
        val tanB = FloatArray(2)

        while (d < length) {
            if (!measure.getPosTan(d, pos, tan)) {
                d += 26f
                continue
            }
            val sample = min(10f, max(4f, length * 0.012f))
            measure.getPosTan((d - sample).coerceAtLeast(0f), null, tanA)
            measure.getPosTan((d + sample).coerceAtMost(length), null, tanB)

            fun normalized(v: FloatArray): Pair<Float, Float> {
                val m = sqrt(v[0] * v[0] + v[1] * v[1]).coerceAtLeast(0.001f)
                return Pair(v[0] / m, v[1] / m)
            }
            val (ax, ay) = normalized(tanA)
            val (bx, by) = normalized(tanB)
            val turn = (acos((ax * bx + ay * by).coerceIn(-1f, 1f)) / 0.55f)
                .coerceIn(0f, 1f)

            val mag = sqrt(tan[0] * tan[0] + tan[1] * tan[1]).coerceAtLeast(0.001f)
            val ux = tan[0] / mag
            val uy = tan[1] / mag
            val nx = -uy
            val ny = ux

            val arrowLength = 10.5f - turn * 4.2f
            val halfWidth = 6.8f - turn * 3.0f
            val spacing = 36f - turn * 16f
            val backX = pos[0] - ux * arrowLength
            val backY = pos[1] - uy * arrowLength

            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 2.7f - turn * 0.9f
            paint.strokeCap = Paint.Cap.ROUND
            paint.color = Color.argb(235, 215, 255, 244)
            paint.setShadowLayer(7f - turn * 2f, 0f, 0f, Color.rgb(0, 255, 190))
            canvas.drawLine(backX + nx * halfWidth, backY + ny * halfWidth, pos[0], pos[1], paint)
            canvas.drawLine(backX - nx * halfWidth, backY - ny * halfWidth, pos[0], pos[1], paint)
            paint.clearShadowLayer()

            d += spacing
        }
    }

}
