package jp.example.greenreader.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import jp.example.greenreader.analysis.Vec3
import jp.example.greenreader.precision.PrecisionSurfaceModel
import kotlin.math.sqrt

class Golfer3DView(context: Context) : View(context) {
    var surface: PrecisionSurfaceModel? = null
        set(value) { field = value; invalidate() }
    var ball: Vec3? = null
        set(value) { field = value; invalidate() }
    var cup: Vec3? = null
        set(value) { field = value; invalidate() }
    var verticalExaggeration = 4f
        set(value) { field = value.coerceIn(1f, 10f); invalidate() }

    private var yawOffset = 0f
    private var lastX = 0f
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { strokeWidth = 2f }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> lastX = event.x
            MotionEvent.ACTION_MOVE -> {
                yawOffset += (event.x - lastX) * 0.003f
                lastX = event.x
                invalidate()
            }
        }
        return true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(0xff0b1410.toInt())
        val s = surface ?: return message(canvas, "3D地形がありません")
        val b = ball ?: return message(canvas, "ボール位置がありません")
        val c = cup ?: return message(canvas, "カップ位置がありません")
        val dx = c.x - b.x
        val dz = c.z - b.z
        val dist = sqrt(dx * dx + dz * dz).coerceAtLeast(0.1f)
        val fx0 = dx / dist
        val fz0 = dz / dist
        val cy = kotlin.math.cos(yawOffset)
        val sy = kotlin.math.sin(yawOffset)
        val fx = fx0 * cy - fz0 * sy
        val fz = fx0 * sy + fz0 * cy
        val rx = -fz
        val rz = fx

        val eyeForward = -0.9f
        val eyeHeight = 1.55f
        val focal = width * 0.9f
        val horizon = height * 0.47f

        paint.color = 0xff72c472.toInt()
        val sorted = s.cells.sortedByDescending { cell ->
            val wx = cell.x - b.x
            val wz = cell.z - b.z
            wx * fx + wz * fz
        }
        for (cell in sorted) {
            val wx = cell.x - b.x
            val wz = cell.z - b.z
            val forward = wx * fx + wz * fz - eyeForward
            if (forward < 0.18f || forward > dist + 2.5f) continue
            val lateral = wx * rx + wz * rz
            if (kotlin.math.abs(lateral) > 4f) continue
            val h = (cell.height - b.y) * verticalExaggeration
            val sx = width * 0.5f + lateral * focal / forward
            val syScreen = horizon - (h - eyeHeight) * focal / forward
            val r = (7f / forward).coerceIn(1.2f, 5.0f)
            paint.alpha = (80 + cell.confidence * 175).toInt().coerceIn(80, 255)
            canvas.drawCircle(sx, syScreen, r, paint)
        }
        paint.alpha = 255
        paint.color = 0xffffffff.toInt(); paint.textSize = 30f
        canvas.drawText("ゴルファー目線 3D  高さ×%.1f".format(verticalExaggeration), 24f, 48f, paint)
        canvas.drawText("左右ドラッグで視点を回転", 24f, 84f, paint)

        val cupForward = dist - eyeForward
        paint.color = 0xffffe080.toInt()
        canvas.drawCircle(
            width * 0.5f,
            horizon - ((c.y - b.y) * verticalExaggeration - eyeHeight) * focal / cupForward,
            12f,
            paint
        )
    }

    private fun message(canvas: Canvas, msg: String) {
        paint.color = 0xffffffff.toInt(); paint.textSize = 34f
        canvas.drawText(msg, 30f, 70f, paint)
    }
}
