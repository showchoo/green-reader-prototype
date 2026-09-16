from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"pattern not found:\n{old[:200]}")
    s = s.replace(old, new, 1)

replace_once(
    "import android.os.Bundle\nimport android.os.SystemClock",
    "import android.os.Bundle\nimport android.os.Handler\nimport android.os.Looper\nimport android.os.SystemClock",
)

replace_once(
    "    private val bg = BackgroundRenderer()\n    private val collector = DepthCollector()",
    """    private val bg = BackgroundRenderer()
    private val collector = DepthCollector()
    private val renderHandler = Handler(Looper.getMainLooper())
    @Volatile private var activityActive = false
    @Volatile private var arSuspendedForResult = false
    private val renderTick = object : Runnable {
        override fun run() {
            if (!activityActive || arSuspendedForResult || gl.visibility != View.VISIBLE) return
            gl.requestRender()
            val fast = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (fast) 33L else 140L)
        }
    }""",
)

replace_once(
    "            renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY",
    "            renderMode = GLSurfaceView.RENDERMODE_WHEN_DIRTY",
)

replace_once(
    "            scanning = true\n            scanButton.text = \"スキャン終了\"",
    "            scanning = true\n            restartRenderLoop()\n            scanButton.text = \"スキャン終了\"",
)

replace_once(
    "        status.text = message\n        captureRequested = true",
    "        status.text = message\n        captureRequested = true\n        restartRenderLoop()",
)

replace_once(
    "        mapToggleButton.text = \"カメラ表示\"\n        overlayToggleButton.text = \"実画像結果\"\n    }\n\n    private fun showOverlay()",
    "        mapToggleButton.text = \"カメラ表示\"\n        overlayToggleButton.text = \"実画像結果\"\n        suspendArForResult()\n    }\n\n    private fun showOverlay()",
)

replace_once(
    "        overlayToggleButton.text = \"カメラ表示\"\n        mapToggleButton.text = \"傾斜マップ\"\n    }\n\n    private fun showCamera()",
    "        overlayToggleButton.text = \"カメラ表示\"\n        mapToggleButton.text = \"傾斜マップ\"\n        suspendArForResult()\n    }\n\n    private fun showCamera()",
)

replace_once(
    "        mapToggleButton.text = \"傾斜マップ\"\n        overlayToggleButton.text = \"実画像結果\"\n    }\n\n    override fun onResume()",
    """        mapToggleButton.text = "傾斜マップ"
        overlayToggleButton.text = "実画像結果"
        resumeArForCamera()
    }

    private fun restartRenderLoop() {
        renderHandler.removeCallbacks(renderTick)
        if (activityActive && !arSuspendedForResult && gl.visibility == View.VISIBLE) {
            renderHandler.post(renderTick)
        }
    }

    private fun suspendArForResult() {
        if (!activityActive || arSuspendedForResult) return
        renderHandler.removeCallbacks(renderTick)
        try {
            gl.onPause()
            session?.pause()
            arSuspendedForResult = true
        } catch (_: Throwable) {
        }
    }

    private fun resumeArForCamera() {
        if (!activityActive) return
        try {
            if (arSuspendedForResult) {
                session?.resume()
                gl.onResume()
                arSuspendedForResult = false
            }
            restartRenderLoop()
        } catch (_: CameraNotAvailableException) {
            status.text = "カメラを再開できません"
        }
    }

    override fun onResume()""",
)

replace_once(
    "        super.onResume()\n        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return",
    "        super.onResume()\n        activityActive = true\n        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return",
)

replace_once(
    "            session?.resume()\n            gl.onResume()",
    """            if (!showMap && !showOverlay) {
                session?.resume()
                gl.onResume()
                arSuspendedForResult = false
                restartRenderLoop()
            } else {
                arSuspendedForResult = true
            }""",
)

replace_once(
    "        super.onPause()\n        scanning = false\n        pendingMark = null\n        gl.onPause()\n        session?.pause()",
    """        super.onPause()
        activityActive = false
        renderHandler.removeCallbacks(renderTick)
        scanning = false
        pendingMark = null
        if (!arSuspendedForResult) {
            gl.onPause()
            session?.pause()
        }""",
)

path.write_text(s, encoding="utf-8")
print("Applied Green Scan power-saving patch")
