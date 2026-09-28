package jp.example.greenreader.ui

import android.content.Context
import android.graphics.BlurMaskFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.SystemClock
import android.view.View
import kotlin.math.max

/**
 * Lightweight live-camera HUD. It never touches AR/Depth data; it is purely visual.
 */
class NeonScanOverlayView(context: Context) : View(context) {
    var scanning: Boolean = false
        set(value) {
            field = value
            invalidate()
        }

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(118, 255, 210)
        textSize = 20f
    }

    init {
        isClickable = false
        isFocusable = false
        setLayerType(LAYER_TYPE_SOFTWARE, null)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width <= 0 || height <= 0) return

        val margin = max(24f, width * 0.035f)
        val top = margin + 90f
        val bottom = height - margin - 290f
        if (bottom <= top) return

        // Subtle scanner grid.
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1f
        paint.color = Color.argb(if (scanning) 42 else 24, 0, 255, 190)
        val stepX = width / 8f
        var x = 0f
        while (x <= width) {
            canvas.drawLine(x, top, x, bottom, paint)
            x += stepX
        }
        val stepY = max(54f, (bottom - top) / 9f)
        var y = top
        while (y <= bottom) {
            canvas.drawLine(0f, y, width.toFloat(), y, paint)
            y += stepY
        }

        drawCorners(canvas, margin, top, width - margin, bottom)

        // Moving scan beam only during an active measurement.
        if (scanning) {
            val cycle = 1800L
            val phase = (SystemClock.uptimeMillis() % cycle) / cycle.toFloat()
            val beamY = top + (bottom - top) * phase
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 2.5f
            paint.color = Color.argb(210, 85, 255, 214)
            paint.setShadowLayer(18f, 0f, 0f, Color.rgb(0, 255, 190))
            canvas.drawLine(margin, beamY, width - margin, beamY, paint)
            paint.clearShadowLayer()

            paint.style = Paint.Style.FILL
            paint.color = Color.argb(25, 0, 255, 170)
            canvas.drawRect(margin, beamY - 18f, width - margin, beamY + 18f, paint)

            text.textAlign = Paint.Align.RIGHT
            text.textSize = 18f
            text.color = Color.rgb(120, 255, 213)
            canvas.drawText("DEPTH SCAN // ACTIVE", width - margin, top - 18f, text)
            postInvalidateOnAnimation()
        } else {
            text.textAlign = Paint.Align.RIGHT
            text.textSize = 17f
            text.color = Color.argb(190, 115, 255, 206)
            canvas.drawText("AR FIELD // READY", width - margin, top - 18f, text)
        }
    }

    private fun drawCorners(canvas: Canvas, l: Float, t: Float, r: Float, b: Float) {
        val c = 34f
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 2.5f
        paint.color = Color.argb(190, 66, 255, 205)
        paint.setShadowLayer(10f, 0f, 0f, Color.rgb(0, 255, 190))

        canvas.drawLine(l, t + c, l, t, paint)
        canvas.drawLine(l, t, l + c, t, paint)
        canvas.drawLine(r - c, t, r, t, paint)
        canvas.drawLine(r, t, r, t + c, paint)
        canvas.drawLine(l, b - c, l, b, paint)
        canvas.drawLine(l, b, l + c, b, paint)
        canvas.drawLine(r - c, b, r, b, paint)
        canvas.drawLine(r, b - c, r, b, paint)

        paint.clearShadowLayer()
    }
}
