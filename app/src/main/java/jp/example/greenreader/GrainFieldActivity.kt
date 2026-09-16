package jp.example.greenreader

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.view.Gravity
import android.view.Surface
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.ar.core.ArCoreApk
import com.google.ar.core.Config
import com.google.ar.core.Session
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.CameraNotAvailableException
import com.google.ar.core.exceptions.UnavailableException
import jp.example.greenreader.analysis.GrainEstimator
import jp.example.greenreader.ar.BackgroundRenderer
import jp.example.greenreader.field.GrainFieldRecorder
import jp.example.greenreader.field.GrainSavedRecord
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class GrainFieldActivity : AppCompatActivity(), GLSurfaceView.Renderer {
    private lateinit var gl: GLSurfaceView
    private lateinit var status: TextView
    private lateinit var axisText: TextView
    private lateinit var confidenceText: TextView
    private lateinit var labelRow: LinearLayout
    private lateinit var recordButton: Button

    private val bg = BackgroundRenderer()
    private var session: Session? = null
    private var viewportW = 1
    private var viewportH = 1
    @Volatile private var recordRequested = false
    @Volatile private var tracking = "AR準備中"
    private var lastRecord: GrainSavedRecord? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(7, 15, 12)
        window.navigationBarColor = Color.rgb(7, 15, 12)
        buildUi()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 201)
        }
    }

    private fun buildUi() {
        val root = FrameLayout(this)
        gl = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setRenderer(this@GrainFieldActivity)
            renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        }
        root.addView(gl, FrameLayout.LayoutParams(-1, -1))

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(14))
            background = GradientDrawable().apply {
                cornerRadius = dp(20).toFloat()
                setColor(Color.argb(205, 8, 20, 15))
                setStroke(dp(1), Color.argb(180, 74, 137, 98))
            }
            addView(TextView(this@GrainFieldActivity).apply {
                text = "GRAIN FIELD LOG"
                setTextColor(Color.rgb(129, 255, 176))
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                letterSpacing = 0.12f
            })
            addView(TextView(this@GrainFieldActivity).apply {
                text = "芝目の“軸”を記録して、後で改善に使う"
                setTextColor(Color.WHITE)
                textSize = 18f
                typeface = Typeface.DEFAULT_BOLD
                setPadding(0, dp(4), 0, 0)
            })
        }
        root.addView(header, FrameLayout.LayoutParams(-1, -2).apply {
            gravity = Gravity.TOP
            setMargins(dp(14), dp(12), dp(14), 0)
        })

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(18))
            background = GradientDrawable().apply {
                cornerRadii = floatArrayOf(dp(28).toFloat(), dp(28).toFloat(), dp(28).toFloat(), dp(28).toFloat(), 0f, 0f, 0f, 0f)
                setColor(Color.argb(238, 8, 18, 14))
                setStroke(dp(1), Color.rgb(44, 75, 58))
            }
        }

        val metrics = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        axisText = metric("--°", "芝目軸")
        confidenceText = metric("--%", "信頼度")
        metrics.addView(axisText, LinearLayout.LayoutParams(0, -2, 1f))
        metrics.addView(confidenceText, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(metrics)

        status = TextView(this).apply {
            text = "芝を画面中央に入れ、端末をできるだけ静かに構えてください"
            setTextColor(Color.rgb(195, 215, 203))
            textSize = 13f
            setPadding(dp(4), dp(10), dp(4), dp(12))
        }
        panel.addView(status)

        recordButton = Button(this).apply {
            text = "●  芝目を記録"
            isAllCaps = false
            textSize = 17f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(7, 30, 15))
            background = rounded(Color.rgb(93, 230, 135), Color.rgb(150, 255, 185), 18)
            setOnClickListener {
                lastRecord = null
                labelRow.visibility = View.GONE
                recordRequested = true
                isEnabled = false
                text = "記録中…"
                status.text = "画像・角度・信頼度・端末姿勢を保存しています"
            }
        }
        panel.addView(recordButton, LinearLayout.LayoutParams(-1, dp(56)))

        labelRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            visibility = View.GONE
            setPadding(0, dp(12), 0, 0)
        }
        labelRow.addView(labelButton("✓ 合ってる", "correct"), LinearLayout.LayoutParams(0, dp(46), 1f))
        labelRow.addView(labelButton("↔ 逆向き", "reversed"), LinearLayout.LayoutParams(0, dp(46), 1f).apply { setMargins(dp(8), 0, dp(8), 0) })
        labelRow.addView(labelButton("? 不明", "unknown"), LinearLayout.LayoutParams(0, dp(46), 1f))
        panel.addView(labelRow)

        panel.addView(TextView(this).apply {
            text = "保存先  Pictures/GreenReaderRecords  +  Download/GreenReaderRecords"
            setTextColor(Color.rgb(111, 142, 123))
            textSize = 11f
            setPadding(dp(4), dp(12), dp(4), 0)
        })

        root.addView(panel, FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM })
        setContentView(root)
    }

    private fun metric(value: String, caption: String): TextView {
        return TextView(this).apply {
            text = "$value\n$caption"
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            textSize = 28f
            typeface = Typeface.DEFAULT_BOLD
            setLineSpacing(0f, 0.84f)
            background = rounded(Color.argb(170, 24, 44, 34), Color.rgb(47, 80, 61), 18)
            setPadding(0, dp(10), 0, dp(10))
        }
    }

    private fun labelButton(title: String, label: String): Button {
        return Button(this).apply {
            text = title
            isAllCaps = false
            textSize = 12f
            setTextColor(Color.WHITE)
            background = rounded(Color.rgb(26, 48, 37), Color.rgb(63, 105, 78), 14)
            setOnClickListener { applyLabel(label) }
        }
    }

    private fun applyLabel(label: String) {
        val rec = lastRecord ?: return
        Thread {
            try {
                GrainFieldRecorder.relabel(this, rec, label)
                runOnUiThread {
                    status.text = when (label) {
                        "correct" -> "ラベル: 合ってる を保存しました"
                        "reversed" -> "ラベル: 逆向き を保存しました"
                        else -> "ラベル: 不明 を保存しました"
                    }
                }
            } catch (e: Throwable) {
                runOnUiThread { status.text = "ラベル保存失敗: ${e.message ?: "不明"}" }
            }
        }.start()
    }

    override fun onResume() {
        super.onResume()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return
        try {
            if (session == null) {
                if (ArCoreApk.getInstance().requestInstall(this, true) == ArCoreApk.InstallStatus.INSTALL_REQUESTED) return
                session = Session(this).also { s ->
                    val cfg = Config(s).apply {
                        focusMode = Config.FocusMode.AUTO
                        if (s.isDepthModeSupported(Config.DepthMode.AUTOMATIC)) depthMode = Config.DepthMode.AUTOMATIC
                    }
                    s.configure(cfg)
                }
            }
            session?.resume()
            gl.onResume()
        } catch (e: UnavailableException) {
            status.text = "ARCoreを開始できません: ${e.message}"
        } catch (_: CameraNotAvailableException) {
            status.text = "カメラを開始できません"
        }
    }

    override fun onPause() {
        super.onPause()
        recordRequested = false
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
            val frame = s.update()
            tracking = frame.camera.trackingState.name
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
            bg.draw(frame)

            if (recordRequested && frame.camera.trackingState == TrackingState.TRACKING) {
                val report = GrainEstimator.estimate(frame)
                if (report == null) {
                    recordRequested = false
                    runOnUiThread {
                        recordButton.isEnabled = true
                        recordButton.text = "●  芝目を記録"
                        status.text = "画像を取得できません。少しだけ端末を動かして再試行してください"
                    }
                    return
                }
                val bitmap = captureGlFrame(viewportW, viewportH)
                val pose = frame.camera.displayOrientedPose
                val t = FloatArray(3).also { pose.getTranslation(it, 0) }
                val q = FloatArray(4).also { pose.getRotationQuaternion(it, 0) }
                recordRequested = false

                Thread {
                    try {
                        val saved = GrainFieldRecorder.save(this, bitmap, report, t, q)
                        bitmap.recycle()
                        lastRecord = saved
                        runOnUiThread {
                            axisText.text = String.format("%.0f°\n芝目軸", report.axisDegrees)
                            confidenceText.text = String.format("%.0f%%\n信頼度", report.confidence * 100f)
                            recordButton.isEnabled = true
                            recordButton.text = "●  もう1件記録"
                            labelRow.visibility = View.VISIBLE
                            status.text = "保存完了: ${saved.id}  /  判定ラベルを付けてください"
                        }
                    } catch (e: Throwable) {
                        bitmap.recycle()
                        runOnUiThread {
                            recordButton.isEnabled = true
                            recordButton.text = "●  芝目を記録"
                            status.text = "保存失敗: ${e.message ?: "不明なエラー"}"
                        }
                    }
                }.start()
            }
        } catch (e: Throwable) {
            if (recordRequested) {
                recordRequested = false
                runOnUiThread {
                    recordButton.isEnabled = true
                    recordButton.text = "●  芝目を記録"
                    status.text = "記録失敗 ($tracking): ${e.message ?: "不明なエラー"}"
                }
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
            val src = y * w
            val dst = (h - 1 - y) * w
            for (x in 0 until w) {
                val p = raw[src + x]
                out[dst + x] = (p and 0xff00ff00.toInt()) or ((p and 0x000000ff) shl 16) or ((p and 0x00ff0000) ushr 16)
            }
        }
        return Bitmap.createBitmap(out, w, h, Bitmap.Config.ARGB_8888)
    }

    private fun rounded(fill: Int, stroke: Int, radiusDp: Int) = GradientDrawable().apply {
        cornerRadius = dp(radiusDp).toFloat()
        setColor(fill)
        setStroke(dp(1), stroke)
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    override fun onRequestPermissionsResult(req: Int, perms: Array<out String>, res: IntArray) {
        super.onRequestPermissionsResult(req, perms, res)
        if (req == 201 && res.firstOrNull() == PackageManager.PERMISSION_GRANTED) recreate()
    }
}
