package jp.example.greenreader

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.PointF
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.os.Bundle
import android.os.SystemClock
import android.view.Gravity
import android.view.MotionEvent
import android.view.Surface
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.ar.core.*
import com.google.ar.core.exceptions.CameraNotAvailableException
import com.google.ar.core.exceptions.NotYetAvailableException
import com.google.ar.core.exceptions.UnavailableException
import jp.example.greenreader.analysis.*
import jp.example.greenreader.ar.BackgroundRenderer
import jp.example.greenreader.ui.CameraOverlayResultView
import jp.example.greenreader.ui.GreenMapView
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class MainActivity : AppCompatActivity(), GLSurfaceView.Renderer {
    private lateinit var gl: GLSurfaceView
    private lateinit var status: TextView
    private lateinit var diagnostics: TextView
    private lateinit var mapView: GreenMapView
    private lateinit var overlayView: CameraOverlayResultView
    private lateinit var stimp: SeekBar
    private lateinit var stimpLabel: TextView
    private lateinit var scanButton: Button
    private lateinit var overlayToggleButton: Button
    private lateinit var mapToggleButton: Button
    private lateinit var testToggleButton: Button

    private var session: Session? = null
    private val bg = BackgroundRenderer()
    private val collector = DepthCollector()
    @Volatile private var latestFrame: Frame? = null
    @Volatile private var trackingStateText: String = "AR準備中"
    @Volatile private var scanning = false
    @Volatile private var autoStopPending = false
    @Volatile private var captureRequested = false
    private var scanStartMs = 0L
    private var markMode = 0
    private var ball: Vec3? = null
    private var cup: Vec3? = null
    private var grain: GrainReport? = null
    private var viewportW = 1
    private var viewportH = 1
    private var showMap = false
    private var showOverlay = false
    private var testMode = false
    private var frameCounter = 0
    private var depthSupported = false
    private var capturedBitmap: Bitmap? = null
    private var capturedBallScreen: PointF? = null
    private var capturedCupScreen: PointF? = null

    private data class PendingMark(val mode: Int, val x: Float, val y: Float, val startedMs: Long)
    @Volatile private var pendingMark: PendingMark? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 100)
        }
    }

    private fun buildUi() {
        val root = FrameLayout(this)

        gl = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setRenderer(this@MainActivity)
            renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
            setOnTouchListener { _, ev ->
                if (ev.action == MotionEvent.ACTION_UP && markMode != 0) {
                    markAt(ev.x, ev.y)
                    true
                } else markMode != 0
            }
        }
        root.addView(gl, FrameLayout.LayoutParams(-1, -1))

        mapView = GreenMapView(this).apply { visibility = View.GONE }
        root.addView(mapView, FrameLayout.LayoutParams(-1, -1))

        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }
        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(14, 12, 14, 14)
            setBackgroundColor(0xD8111111.toInt())
        }

        status = TextView(this).apply {
            text = "①ボール ②カップ ③スキャン開始"
            setTextColor(0xffffffff.toInt())
            textSize = 16f
            setPadding(6, 4, 6, 8)
        }
        panel.addView(status)

        diagnostics = TextView(this).apply {
            visibility = View.GONE
            setTextColor(0xffd5ffd5.toInt())
            textSize = 12f
            text = "テストモード"
            setPadding(6, 0, 6, 6)
        }
        panel.addView(diagnostics)

        fun button(text: String, action: () -> Unit) = Button(this).apply {
            this.text = text
            isAllCaps = false
            setOnClickListener { action() }
        }

        val row1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row1.addView(button("ボール") {
            showCamera()
            pendingMark = null
            markMode = 1
            status.text = "ボールの中心付近を1回タップしてください"
        }, LinearLayout.LayoutParams(0, -2, 1f))
        row1.addView(button("カップ") {
            showCamera()
            pendingMark = null
            markMode = 2
            status.text = "カップの中心付近を1回タップしてください"
        }, LinearLayout.LayoutParams(0, -2, 1f))
        scanButton = button("スキャン開始") { toggleScan() }
        row1.addView(scanButton, LinearLayout.LayoutParams(0, -2, 1.25f))
        panel.addView(row1)

        val row2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row2.addView(button("芝目解析") { analyzeGrain() }, LinearLayout.LayoutParams(0, -2, 1f))
        row2.addView(button("解析") { requestCaptureAndAnalyze("実画像を保存して解析中…") }, LinearLayout.LayoutParams(0, -2, 1f))
        row2.addView(button("リセット") { resetAll() }, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(row2)

        val row3 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        overlayToggleButton = button("実画像結果") { if (showOverlay) showCamera() else showOverlay() }
        mapToggleButton = button("傾斜マップ") { if (showMap) showCamera() else showMap() }
        testToggleButton = button("テストモード") { toggleTestMode() }
        row3.addView(overlayToggleButton, LinearLayout.LayoutParams(0, -2, 1f))
        row3.addView(mapToggleButton, LinearLayout.LayoutParams(0, -2, 1f))
        row3.addView(testToggleButton, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(row3)

        stimpLabel = TextView(this).apply {
            setTextColor(0xffffffff.toInt())
            text = "Stimp: 9.0"
        }
        panel.addView(stimpLabel)
        stimp = SeekBar(this).apply {
            max = 50
            progress = 20
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(s: SeekBar?, p: Int, from: Boolean) {
                    stimpLabel.text = String.format("Stimp: %.1f", 7f + p / 10f)
                }
                override fun onStartTrackingTouch(s: SeekBar?) {}
                override fun onStopTrackingTouch(s: SeekBar?) {
                    if (mapView.report != null) analyze(updateStatus = false, showResult = false)
                }
            })
        }
        panel.addView(stimp)

        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }
        root.addView(panel, lp)
        setContentView(root)
    }

    private fun toggleScan() {
        if (!scanning) {
            if (ball == null || cup == null) {
                status.text = "先にボールとカップを設定してください"
                return
            }
            pendingMark = null
            showCamera()
            collector.clear()
            autoStopPending = false
            captureRequested = false
            scanStartMs = SystemClock.elapsedRealtime()
            scanning = true
            scanButton.text = "スキャン終了"
            status.text = "スキャン中… 必要なデータが取れ次第、自動で終了します"
        } else {
            requestCaptureAndAnalyze("スキャン終了。実画像を保存して解析中…")
        }
    }

    private fun requestCaptureAndAnalyze(message: String) {
        if (ball == null || cup == null) {
            status.text = "先にボールとカップを設定してください"
            return
        }
        pendingMark = null
        scanning = false
        autoStopPending = true
        scanButton.text = "スキャン開始"
        showCamera()
        status.text = message
        captureRequested = true
    }

    private fun toggleTestMode() {
        testMode = !testMode
        diagnostics.visibility = if (testMode) View.VISIBLE else View.GONE
        testToggleButton.text = if (testMode) "テストOFF" else "テストモード"
        if (testMode) updateDiagnostics()
    }

    private fun resetAll() {
        scanning = false
        autoStopPending = false
        captureRequested = false
        pendingMark = null
        markMode = 0
        scanButton.text = "スキャン開始"
        ball = null
        cup = null
        grain = null
        collector.clear()
        mapView.report = null
        mapView.advice = null
        mapView.grain = null
        overlayView.clear()
        capturedBitmap?.recycle()
        capturedBitmap = null
        capturedBallScreen = null
        capturedCupScreen = null
        showCamera()
        status.text = "リセットしました。ボール位置から設定してください"
    }

    private fun showMap() {
        if (mapView.report == null) {
            status.text = "まだ解析結果がありません"
            return
        }
        showMap = true
        showOverlay = false
        gl.visibility = View.GONE
        overlayView.visibility = View.GONE
        mapView.visibility = View.VISIBLE
        mapToggleButton.text = "カメラ表示"
        overlayToggleButton.text = "実画像結果"
    }

    private fun showOverlay() {
        if (overlayView.report == null || overlayView.frameBitmap == null) {
            status.text = "まだ実画像の解析結果がありません"
            return
        }
        showMap = false
        showOverlay = true
        gl.visibility = View.GONE
        mapView.visibility = View.GONE
        overlayView.visibility = View.VISIBLE
        overlayToggleButton.text = "カメラ表示"
        mapToggleButton.text = "傾斜マップ"
    }

    private fun showCamera() {
        showMap = false
        showOverlay = false
        mapView.visibility = View.GONE
        overlayView.visibility = View.GONE
        gl.visibility = View.VISIBLE
        mapToggleButton.text = "傾斜マップ"
        overlayToggleButton.text = "実画像結果"
    }

    override fun onResume() {
        super.onResume()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return
        try {
            if (session == null) {
                when (ArCoreApk.getInstance().requestInstall(this, true)) {
                    ArCoreApk.InstallStatus.INSTALL_REQUESTED -> return
                    else -> {}
                }
                session = Session(this).also { s ->
                    depthSupported = s.isDepthModeSupported(Config.DepthMode.AUTOMATIC)
                    val c = Config(s).apply {
                        focusMode = Config.FocusMode.AUTO
                        planeFindingMode = Config.PlaneFindingMode.HORIZONTAL
                        if (depthSupported) depthMode = Config.DepthMode.AUTOMATIC
                    }
                    s.configure(c)
                }
            }
            session?.resume()
            gl.onResume()
        } catch (e: UnavailableException) {
            status.text = "ARCoreを開始できません: ${e.message}"
        } catch (e: CameraNotAvailableException) {
            status.text = "カメラを開始できません"
        }
    }

    override fun onPause() {
        super.onPause()
        scanning = false
        pendingMark = null
        gl.onPause()
        session?.pause()
    }

    override fun onSurfaceCreated(unused: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        bg.createOnGlThread()
        session?.setCameraTextureName(bg.textureId)
    }

    override fun onSurfaceChanged(unused: GL10?, w: Int, h: Int) {
        viewportW = w
        viewportH = h
        GLES20.glViewport(0, 0, w, h)
    }

    override fun onDrawFrame(unused: GL10?) {
        val s = session ?: return
        try {
            s.setDisplayGeometry(display?.rotation ?: Surface.ROTATION_0, viewportW, viewportH)
            if (bg.textureId != -1) s.setCameraTextureName(bg.textureId)
            val f = s.update()
            latestFrame = f
            trackingStateText = f.camera.trackingState.name
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
            bg.draw(f)

            if (f.camera.trackingState == TrackingState.TRACKING) {
                tryResolvePendingMark(f)
            }

            if (scanning && f.camera.trackingState == TrackingState.TRACKING) {
                collector.integrate(f, pixelStrideStep = 4)
                maybeAutoFinishScan()
            }

            if (captureRequested && f.camera.trackingState == TrackingState.TRACKING) {
                val bitmap = captureGlFrame(viewportW, viewportH)
                val projectedBall = ball?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = cup?.let { projectWorldPoint(f.camera, it) }
                capturedBitmap?.recycle()
                capturedBitmap = bitmap
                capturedBallScreen = projectedBall
                capturedCupScreen = projectedCup
                captureRequested = false
                runOnUiThread { analyze(updateStatus = true, showResult = true) }
            }

            frameCounter++
            if (testMode && frameCounter % 15 == 0) runOnUiThread { updateDiagnostics() }
            if (scanning && frameCounter % 12 == 0) {
                val elapsed = ((SystemClock.elapsedRealtime() - scanStartMs) / 100L) / 10f
                val count = collector.size()
                runOnUiThread {
                    if (scanning) status.text = String.format("スキャン中 %.1f秒 / 取得点 %,d", elapsed, count)
                }
            }
        } catch (e: Throwable) {
            if (captureRequested) {
                captureRequested = false
                runOnUiThread { status.text = "実画像の取得に失敗しました: ${e.message ?: "不明なエラー"}" }
            }
        }
    }

    private fun maybeAutoFinishScan() {
        if (!scanning || autoStopPending) return
        val elapsed = SystemClock.elapsedRealtime() - scanStartMs
        val b = ball ?: return
        val c = cup ?: return

        if (elapsed >= 1000L && frameCounter % 6 == 0) {
            val candidate = SlopeAnalyzer.analyze(collector.snapshot(), b, c)
            if (candidate != null && candidate.pointCount >= 100) {
                autoStopPending = true
                scanning = false
                captureRequested = true
                runOnUiThread {
                    scanButton.text = "スキャン開始"
                    status.text = "必要なデータが取れました。実画像を保存して解析中…"
                }
                return
            }
        }

        if (elapsed >= 3000L) {
            autoStopPending = true
            scanning = false
            captureRequested = true
            runOnUiThread {
                scanButton.text = "スキャン開始"
                status.text = "3秒スキャン完了。実画像を保存して解析中…"
            }
        }
    }

    private fun captureGlFrame(w: Int, h: Int): Bitmap {
        GLES20.glFinish()
        val buffer = ByteBuffer.allocateDirect(w * h * 4).order(ByteOrder.LITTLE_ENDIAN)
        GLES20.glReadPixels(0, 0, w, h, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, buffer)
        val raw = IntArray(w * h)
        buffer.rewind()
        buffer.asIntBuffer().get(raw)
        val out = IntArray(w * h)
        for (y in 0 until h) {
            val srcRow = y * w
            val dstRow = (h - 1 - y) * w
            for (x in 0 until w) {
                val p = raw[srcRow + x]
                val corrected = (p and 0xff00ff00.toInt()) or
                    ((p and 0x000000ff) shl 16) or
                    ((p and 0x00ff0000) ushr 16)
                out[dstRow + x] = corrected
            }
        }
        return Bitmap.createBitmap(out, w, h, Bitmap.Config.ARGB_8888)
    }

    private fun projectWorldPoint(camera: Camera, p: Vec3): PointF? {
        val view = FloatArray(16)
        val projection = FloatArray(16)
        val vp = FloatArray(16)
        val clip = FloatArray(4)
        camera.getViewMatrix(view, 0)
        camera.getProjectionMatrix(projection, 0, 0.05f, 100f)
        Matrix.multiplyMM(vp, 0, projection, 0, view, 0)
        Matrix.multiplyMV(clip, 0, vp, 0, floatArrayOf(p.x, p.y, p.z, 1f), 0)
        val w = clip[3]
        if (w <= 0.0001f) return null
        val ndcX = clip[0] / w
        val ndcY = clip[1] / w
        if (ndcX !in -1.25f..1.25f || ndcY !in -1.25f..1.25f) return null
        return PointF(
            (ndcX + 1f) * 0.5f * viewportW,
            (1f - ndcY) * 0.5f * viewportH
        )
    }

    private fun updateDiagnostics() {
        val b = if (ball != null) "済" else "未"
        val c = if (cup != null) "済" else "未"
        val wait = if (pendingMark != null) "WAIT" else "-"
        val shot = if (capturedBitmap != null) "済" else "未"
        diagnostics.text = "TEST  AR:$trackingStateText  Depth:${if (depthSupported) "対応" else "非対応"}  点:${collector.size()}  Ball:$b  Cup:$c  Tap:$wait  Scan:${if (scanning) "ON" else "OFF"}  Shot:$shot"
    }

    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return
        val f = latestFrame
        if (f == null) {
            status.text = "ARの準備中です。端末を少し動かしてください"
            return
        }

        val p = resolveMarkPoint(f, x, y)
        if (p != null) {
            applyMark(mode, p)
            return
        }

        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime())
        markMode = 0
        status.text = "位置を取得中… そのまま端末を少しだけ動かしてください"
    }

    private fun tryResolvePendingMark(frame: Frame) {
        val pending = pendingMark ?: return
        val elapsed = SystemClock.elapsedRealtime() - pending.startedMs
        if (elapsed > 1800L) {
            pendingMark = null
            markMode = pending.mode
            runOnUiThread {
                status.text = if (pending.mode == 1) {
                    "ボール位置を取得できませんでした。もう一度1回だけタップしてください"
                } else {
                    "カップ位置を取得できませんでした。もう一度1回だけタップしてください"
                }
            }
            return
        }

        val p = resolveMarkPoint(frame, pending.x, pending.y) ?: return
        pendingMark = null
        runOnUiThread { applyMark(pending.mode, p) }
    }

    private fun applyMark(mode: Int, p: Vec3) {
        pendingMark = null
        markMode = 0
        if (mode == 1) {
            ball = p
            status.text = "ボール位置を設定しました。次にカップを設定"
        } else {
            cup = p
            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        if (testMode) updateDiagnostics()
    }

    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return exactHitPoint(frame, x, y)
            ?: depthPointAtTap(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
    }

    private fun exactHitPoint(frame: Frame, x: Float, y: Float): Vec3? {
        val hit = frame.hitTest(x, y).firstOrNull { h ->
            val t = h.trackable
            (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
        } ?: return null
        val tr = hit.hitPose.translation
        return Vec3(tr[0], tr[1], tr[2])
    }

    private fun tinyNearbyHitPoint(frame: Frame, x: Float, y: Float): Vec3? {
        val offsets = arrayOf(
            10f to 0f, -10f to 0f, 0f to 10f, 0f to -10f,
            10f to 10f, 10f to -10f, -10f to 10f, -10f to -10f,
            20f to 0f, -20f to 0f, 0f to 20f, 0f to -20f
        )
        for ((dx, dy) in offsets) {
            val sx = (x + dx).coerceIn(0f, viewportW.toFloat() - 1f)
            val sy = (y + dy).coerceIn(0f, viewportH.toFloat() - 1f)
            val hit = frame.hitTest(sx, sy).firstOrNull { h ->
                val t = h.trackable
                (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
            }
            if (hit != null) {
                val tr = hit.hitPose.translation
                return Vec3(tr[0], tr[1], tr[2])
            }
        }
        return null
    }

    private fun depthPointAtTap(frame: Frame, x: Float, y: Float): Vec3? {
        if (viewportW <= 1 || viewportH <= 1) return null
        return try {
            frame.acquireDepthImage16Bits().use { img ->
                val inCoords = floatArrayOf((x / viewportW).coerceIn(0f, 1f), (y / viewportH).coerceIn(0f, 1f))
                val texCoords = FloatArray(2)
                frame.transformCoordinates2d(Coordinates2d.VIEW_NORMALIZED, inCoords, Coordinates2d.TEXTURE_NORMALIZED, texCoords)
                val tx = texCoords[0].coerceIn(0f, 0.9999f)
                val ty = texCoords[1].coerceIn(0f, 0.9999f)
                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                val plane = img.planes[0]
                val buf = plane.buffer.order(ByteOrder.LITTLE_ENDIAN)

                var bestX = -1
                var bestY = -1
                var bestMm = 0
                var bestD2 = Int.MAX_VALUE
                for (radius in listOf(0, 1, 2, 3, 4)) {
                    for (dy in -radius..radius) {
                        for (dx in -radius..radius) {
                            if (radius > 0 && kotlin.math.max(kotlin.math.abs(dx), kotlin.math.abs(dy)) != radius) continue
                            val xx = (px + dx).coerceIn(0, img.width - 1)
                            val yy = (py + dy).coerceIn(0, img.height - 1)
                            val idx = yy * plane.rowStride + xx * plane.pixelStride
                            if (idx + 1 >= buf.limit()) continue
                            val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                            if (mm !in 200..12000) continue
                            val d2 = dx * dx + dy * dy
                            if (d2 < bestD2) {
                                bestD2 = d2
                                bestX = xx
                                bestY = yy
                                bestMm = mm
                            }
                        }
                    }
                    if (bestX >= 0) break
                }
                if (bestX < 0) return null

                val values = ArrayList<Int>(25)
                for (dy in -2..2) for (dx in -2..2) {
                    val xx = (bestX + dx).coerceIn(0, img.width - 1)
                    val yy = (bestY + dy).coerceIn(0, img.height - 1)
                    val idx = yy * plane.rowStride + xx * plane.pixelStride
                    if (idx + 1 < buf.limit()) {
                        val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                        if (mm in 200..12000) values += mm
                    }
                }
                val z = if (values.isNotEmpty()) {
                    values.sort()
                    values[values.size / 2] / 1000f
                } else bestMm / 1000f

                val intr = frame.camera.textureIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val sampleTx = (bestX + 0.5f) / img.width.toFloat()
                val sampleTy = (bestY + 0.5f) / img.height.toFloat()
                val u = sampleTx * dims[0]
                val v = sampleTy * dims[1]
                val cx = (u - principal[0]) / focal[0] * z
                val cy = -(v - principal[1]) / focal[1] * z
                val world = frame.camera.pose.transformPoint(floatArrayOf(cx, cy, -z))
                Vec3(world[0], world[1], world[2])
            }
        } catch (_: NotYetAvailableException) {
            null
        } catch (_: Throwable) {
            null
        }
    }

    private fun analyzeGrain() {
        val f = latestFrame ?: run {
            status.text = "カメラ画像がまだありません"
            return
        }
        grain = GrainEstimator.estimate(f)
        mapView.grain = grain
        val g = grain
        status.text = if (g == null) {
            "芝画像を取得できません。少し動かして再試行"
        } else {
            String.format("芝目軸 %.0f° / 信頼度 %.0f%% ※順目・逆目はまだ未確定", g.axisDegrees, g.confidence * 100)
        }
    }

    private fun analyze(updateStatus: Boolean = true, showResult: Boolean = true) {
        scanning = false
        autoStopPending = false
        scanButton.text = "スキャン開始"
        val b = ball
        val c = cup
        if (b == null || c == null) {
            if (updateStatus) status.text = "先にボールとカップを設定してください"
            return
        }
        val report = SlopeAnalyzer.analyze(collector.snapshot(), b, c)
        if (report == null) {
            if (updateStatus) status.text = "データ不足です。もう一度3秒スキャンしてください"
            return
        }
        val st = 7f + stimp.progress / 10f
        val adv = PuttAdvisor.advise(report, st, grain)
        mapView.report = report
        mapView.advice = adv
        mapView.grain = grain

        val image = capturedBitmap
        val bp = capturedBallScreen
        val cp = capturedCupScreen
        if (image != null && bp != null && cp != null) {
            overlayView.setResult(image, bp, cp, report, adv)
        } else if (!updateStatus && overlayView.report != null) {
            overlayView.updateAdvice(adv)
        }

        if (updateStatus) {
            val dir = if (adv.aimOffsetCm >= 0) "左" else "右"
            status.text = String.format(
                "解析完了: %.2fm / 縦 %.1f%% / 横 %.1f%% / %s %.0fcm狙い / 点%d",
                report.distanceMeters,
                report.overallLongitudinalPercent,
                report.overallCrossPercent,
                dir,
                kotlin.math.abs(adv.aimOffsetCm),
                report.pointCount
            )
            if (showResult) {
                if (image != null && bp != null && cp != null) {
                    showOverlay()
                } else {
                    status.text = status.text.toString() + " / ボールかカップが画面外のため傾斜マップを表示"
                    showMap()
                }
            }
        }
        if (testMode) updateDiagnostics()
    }

    override fun onRequestPermissionsResult(req: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(req, perms, res)
        if (req == 100 && res.firstOrNull() == PackageManager.PERMISSION_GRANTED) recreate()
    }
}
