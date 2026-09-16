package jp.example.greenreader

import android.Manifest
import android.content.pm.PackageManager
import android.opengl.GLES20
import android.opengl.GLSurfaceView
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
import jp.example.greenreader.ui.GreenMapView
import java.nio.ByteOrder
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class MainActivity : AppCompatActivity(), GLSurfaceView.Renderer {
    private lateinit var gl: GLSurfaceView
    private lateinit var status: TextView
    private lateinit var diagnostics: TextView
    private lateinit var mapView: GreenMapView
    private lateinit var stimp: SeekBar
    private lateinit var stimpLabel: TextView
    private lateinit var scanButton: Button
    private lateinit var mapToggleButton: Button
    private lateinit var testToggleButton: Button

    private var session: Session? = null
    private val bg = BackgroundRenderer()
    private val collector = DepthCollector()
    @Volatile private var latestFrame: Frame? = null
    @Volatile private var trackingStateText: String = "AR準備中"
    @Volatile private var scanning = false
    @Volatile private var autoStopPending = false
    private var scanStartMs = 0L
    private var markMode = 0
    private var ball: Vec3? = null
    private var cup: Vec3? = null
    private var grain: GrainReport? = null
    private var viewportW = 1
    private var viewportH = 1
    private var showMap = false
    private var testMode = false
    private var frameCounter = 0
    private var depthSupported = false

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

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(14, 12, 14, 14)
            setBackgroundColor(0xD8111111.toInt())
        }

        // 操作メッセージは画面最上部ではなく、ボタンのすぐ上に表示する。
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
            markMode = 1
            status.text = "画面上のボール位置をタップ"
        }, LinearLayout.LayoutParams(0, -2, 1f))
        row1.addView(button("カップ") {
            showCamera()
            markMode = 2
            status.text = "画面上のカップ位置をタップ"
        }, LinearLayout.LayoutParams(0, -2, 1f))
        scanButton = button("スキャン開始") { toggleScan() }
        row1.addView(scanButton, LinearLayout.LayoutParams(0, -2, 1.25f))
        panel.addView(row1)

        val row2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row2.addView(button("芝目解析") { analyzeGrain() }, LinearLayout.LayoutParams(0, -2, 1f))
        row2.addView(button("解析") { analyze() }, LinearLayout.LayoutParams(0, -2, 1f))
        row2.addView(button("リセット") { resetAll() }, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(row2)

        val row3 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        mapToggleButton = button("結果マップ") { if (showMap) showCamera() else showMap() }
        testToggleButton = button("テストモード") { toggleTestMode() }
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
                    if (mapView.report != null) analyze(updateStatus = false)
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
            showCamera()
            collector.clear()
            autoStopPending = false
            scanStartMs = SystemClock.elapsedRealtime()
            scanning = true
            scanButton.text = "スキャン終了"
            status.text = "スキャン中… 必要なデータが取れ次第、自動で終了します"
        } else {
            scanning = false
            autoStopPending = true
            scanButton.text = "スキャン開始"
            status.text = "スキャン終了。解析しています…"
            analyze()
        }
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
        scanButton.text = "スキャン開始"
        ball = null
        cup = null
        grain = null
        collector.clear()
        mapView.report = null
        mapView.advice = null
        mapView.grain = null
        showCamera()
        status.text = "リセットしました。ボール位置から設定してください"
    }

    private fun showMap() {
        if (mapView.report == null) {
            status.text = "まだ解析結果がありません"
            return
        }
        showMap = true
        gl.visibility = View.GONE
        mapView.visibility = View.VISIBLE
        mapToggleButton.text = "カメラ表示"
    }

    private fun showCamera() {
        showMap = false
        mapView.visibility = View.GONE
        gl.visibility = View.VISIBLE
        mapToggleButton.text = "結果マップ"
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

            if (scanning && f.camera.trackingState == TrackingState.TRACKING) {
                collector.integrate(f, pixelStrideStep = 4)
                maybeAutoFinishScan()
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
        } catch (_: Throwable) {
        }
    }

    private fun maybeAutoFinishScan() {
        if (!scanning || autoStopPending) return
        val elapsed = SystemClock.elapsedRealtime() - scanStartMs
        val b = ball ?: return
        val c = cup ?: return

        // 最低約1秒は複数フレームを集める。その後は実際に解析可能になった瞬間に終了する。
        if (elapsed >= 1000L && frameCounter % 6 == 0) {
            val candidate = SlopeAnalyzer.analyze(collector.snapshot(), b, c)
            if (candidate != null && candidate.pointCount >= 100) {
                autoStopPending = true
                scanning = false
                runOnUiThread {
                    scanButton.text = "スキャン開始"
                    status.text = "必要なデータが取れました。解析中…"
                    analyze()
                }
                return
            }
        }

        // 条件が悪い場合も3秒で一度解析し、無駄に待たせない。
        if (elapsed >= 3000L) {
            autoStopPending = true
            scanning = false
            runOnUiThread {
                scanButton.text = "スキャン開始"
                status.text = "3秒スキャン完了。解析中…"
                analyze()
            }
        }
    }

    private fun updateDiagnostics() {
        val b = if (ball != null) "済" else "未"
        val c = if (cup != null) "済" else "未"
        diagnostics.text = "TEST  AR:$trackingStateText  Depth:${if (depthSupported) "対応" else "非対応"}  点:${collector.size()}  Ball:$b  Cup:$c  Scan:${if (scanning) "ON" else "OFF"}"
    }

    private fun markAt(x: Float, y: Float) {
        val f = latestFrame ?: run {
            status.text = "ARの準備中です。端末を少し動かしてから再試行してください"
            return
        }

        val normalHit = f.hitTest(x, y).firstOrNull { h ->
            val t = h.trackable
            (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
        }
        val p = normalHit?.hitPose?.translation?.let { Vec3(it[0], it[1], it[2]) }
            ?: depthPointAtTap(f, x, y)

        if (p == null) {
            status.text = "深度が取れていません。床/芝面を映して端末を20〜50cm動かしてから再タップ"
            return
        }
        if (markMode == 1) {
            ball = p
            status.text = "ボール位置を設定しました。次にカップを設定"
        } else {
            cup = p
            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        markMode = 0
        if (testMode) updateDiagnostics()
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
                val values = ArrayList<Int>(49)
                for (dy in -3..3) for (dx in -3..3) {
                    val xx = (px + dx).coerceIn(0, img.width - 1)
                    val yy = (py + dy).coerceIn(0, img.height - 1)
                    val idx = yy * plane.rowStride + xx * plane.pixelStride
                    if (idx + 1 < buf.limit()) {
                        val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                        if (mm in 200..12000) values += mm
                    }
                }
                if (values.isEmpty()) return null
                values.sort()
                val z = values[values.size / 2] / 1000f
                val intr = frame.camera.textureIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val u = tx * dims[0]
                val v = ty * dims[1]
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

    private fun analyze(updateStatus: Boolean = true) {
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
            showMap()
        }
        if (testMode) updateDiagnostics()
    }

    override fun onRequestPermissionsResult(req: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(req, perms, res)
        if (req == 100 && res.firstOrNull() == PackageManager.PERMISSION_GRANTED) recreate()
    }
}
