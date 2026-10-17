"""Generate upgrade-compatible v11.2 LIVE DEPTH16 preview for isolated research.

Apply reproducible source instrumentation AFTER the locked v11.1 generator.
Do NOT alter existing depth/IMU ZIP schema or production putting calculations.
"""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"scripts/build_precision_v111_camera2_sensor_evidence.py"],
               cwd=ROOT,check=True)

def patch(path, old, new):
    content=path.read_text(encoding="utf-8")
    if content.count(old)!=1:
        raise RuntimeError(f"Expected exactly one '{old[:80]}' in {path}")
    path.write_text(content.replace(old,new,1),encoding="utf-8")

gradle=ROOT/"app/build.gradle.kts"
patch(gradle, "versionCode = 1110", "versionCode = 1120")
patch(gradle, 'versionName = "11.1-depth16-imu-evidence"',
              'versionName = "11.2-depth16-live-preview"')

main=ROOT/"app/src/main/java/jp/example/greenreader/MainActivity.kt"
s=main.read_text(encoding="utf-8")
old="Precision 11.1 Camera2 IMU研究"
if s.count(old)<2:raise RuntimeError("Expected original v11.1 MainActivity research links")
main.write_text(s.replace(old,"Precision 11.2 DEPTH16プレビュー研究"),encoding="utf-8")

capture=ROOT/"app/src/main/java/jp/example/greenreader/Camera2DepthCaptureActivity.kt"
patch(capture,
  "import android.graphics.ImageFormat\n",
  "import android.graphics.ImageFormat\nimport android.graphics.Bitmap\nimport android.graphics.Color\n")
patch(capture,
  "import android.widget.LinearLayout\n",
  "import android.widget.LinearLayout\nimport android.widget.ImageView\n")

patch(capture,
  "    private lateinit var status:TextView\n",
  """    private lateinit var status:TextView
    private lateinit var depthPreview:ImageView
    @Volatile private var previewConfigured=false
    @Volatile private var captureReady=false
    private var lastPreviewTimestampNs=0L
""")
patch(capture,
  'text="Camera2 深度＋IMU（研究専用）"',
  'text="Camera2 ライブ深度プレビュー（研究専用）"')
patch(capture,
  '''text="背面カメラを床に向けてから開始してください。\\n"+
                "数秒間、ほぼ静止したままDEPTH16画像を記録します。\\n"+
                "まだ傾斜精度は保証されていません。"''',
  '''text="DEPTH16プレビュー準備中。ピンク=距離無効、水色=急な距離変化。\\n"+
                "板とその周囲がすべて映っているのを確認してから記録してください。\\n"+
                "距離の正確さ・板の自動識別は未証明です。"''')

patch(capture,
  '''        layout.addView(status)
        button=Button(this).apply {''',
  '''        layout.addView(status)
        depthPreview=ImageView(this).apply {
            adjustViewBounds=true
            scaleType=ImageView.ScaleType.FIT_CENTER
            minimumHeight=240
            setBackgroundColor(Color.DKGRAY)
            contentDescription="Camera2 DEPTH16距離のライブ診断画像。ピンクは距離無効、水色は距離の段差。"
        }
        layout.addView(depthPreview,LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,0,1.0f))
        button=Button(this).apply {''')
patch(capture,
  'text="深度データ取得開始"',
  'text="深度画像を確認して記録開始"')
patch(capture,
  '''        sensorManager=getSystemService(SENSOR_SERVICE) as SensorManager
    }''',
  '''        sensorManager=getSystemService(SENSOR_SERVICE) as SensorManager
        ui.postDelayed({
            if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED) {
                setStatus("カメラ権限を許可してからアプリを開き直してください。")
            } else if(!finishing) {
                worker.post { openCamera() }
            }
        },START_DELAY_MS)
    }''')

patch(capture,
  '''    private fun beginCapture() {
        if(started)return
        started=true
        button.text="取得を終了して保存"
        if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED) {
            recordError("CAMERA_PERMISSION_NOT_GRANTED")
            requestFinish("permission_denied")
            return
        }
        setStatus("ARCoreがカメラを解放するまで準備しています…")
        worker.post { registerResearchSensors() }
        ui.postDelayed({if(!finishing)requestFinish("watchdog_timeout")},WATCHDOG_MS)
        ui.postDelayed({if(!finishing)worker.post {openCamera()}},START_DELAY_MS)
    }''',
  '''    private fun beginCapture() {
        if(started)return
        if(!previewConfigured) {
            setStatus("DEPTH16プレビュー準備中です。カメラが開くまで記録できません。")
            return
        }
        started=true
        button.text="取得を終了して保存"
        setStatus("固定したままIMUを準備しています。記録開始まで約1秒です。")
        worker.post {
            registerResearchSensors()
            worker.postDelayed({
                if(!finishing) {
                    captureReady=true
                    setStatus("深度画像を記録中。固定したままにしてください。")
                }
            },1200L)
        }
        ui.postDelayed({if(!finishing)requestFinish("watchdog_timeout")},WATCHDOG_MS)
    }''')
patch(capture,
  '''                            setStatus("深度画像を収集中。床を映したまま静止してください。")''',
  '''                            previewConfigured=true
                            setStatus("深度画像のライブプレビュー中。板の四辺と周囲の床を確認してから記録開始。\\n"+
                                "水色は相対的な距離段差。物理的な板境界とは限りません。")''')

patch(capture,
  '''        img.use {image ->
            if(finishing || frameCount>=MAX_FRAMES)return
            try {''',
  '''        img.use {image ->
            if(finishing)return
            try {''')
patch(capture,
  '''                val stats=PrecisionDepth16Codec.summary(raw,width,height)
                val next=frameCount+1''',
  '''                maybeShowDepthPreview(raw,image.timestamp)
                // The Camera2 stream remains active for aiming. No frames are
                // stored or counted until the user starts the bounded capture.
                if(!captureReady || frameCount>=MAX_FRAMES)return
                val stats=PrecisionDepth16Codec.summary(raw,width,height)
                val next=frameCount+1''')

patch(capture,
  "    private fun requestFinish(reason:String) {",
  '''    private fun maybeShowDepthPreview(raw:ByteArray,timestampNs:Long) {
        // Preview at at most ~3 fps; bounded CPU, no external RGB camera.
        if(timestampNs-lastPreviewTimestampNs < 300_000_000L)return
        lastPreviewTimestampNs=timestampNs
        val count=width*height
        if(raw.size!=count*2)return
        fun range(i:Int):Int {
            val k=i*2
            return ((raw[k].toInt() and 255) or
                ((raw[k+1].toInt() and 255) shl 8)) and 8191
        }
        val samples=ArrayList<Int>(count/100+1)
        for(i in 0 until count step 97) {
            val mm=range(i)
            if(mm>0)samples.add(mm)
        }
        if(samples.size<100)return
        samples.sort()
        val lo=samples[samples.size/50]
        val hi=samples[samples.size*49/50].coerceAtLeast(lo+1)
        val colors=IntArray(count)
        for(y in 0 until height) {
            for(x in 0 until width) {
                val i=y*width+x
                val mm=range(i)
                if(mm==0) {
                    colors[i]=Color.rgb(229,30,130)
                    continue
                }
                // Highlight local depth jumps from the same DEPTH16 image.
                // A jump is only an image-space candidate, never a board ID.
                val dx=if(x+4<width)range(i+4) else 0
                val dy=if(y+4<height)range(i+width*4) else 0
                val edge=(dx>0 && kotlin.math.abs(mm-dx)>=35) ||
                    (dy>0 && kotlin.math.abs(mm-dy)>=35)
                colors[i]=if(edge) Color.rgb(32,236,202) else {
                    val gray=((mm-lo)*255/(hi-lo)).coerceIn(0,255)
                    Color.rgb(gray,gray,gray)
                }
            }
        }
        val bitmap=Bitmap.createBitmap(colors,width,height,Bitmap.Config.ARGB_8888)
        ui.post {
            if(!finishing && !isFinishing && !isDestroyed) {
                depthPreview.setImageBitmap(bitmap)
            } else bitmap.recycle()
        }
    }

    private fun requestFinish(reason:String) {''')
# Preview must run without draining IMU evidence / writing data.
# Production source remains unchanged by this generator.
subprocess.run([sys.executable,"scripts/verify_precision_v112_depth_preview.py"],
               cwd=ROOT,check=True)
print("v11.2 live DEPTH16 preview: capture on user tap only, no certified grade")
