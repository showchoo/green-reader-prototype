from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.7.4 pattern not found:\n{old[:220]}")
    s = s.replace(old, new, 1)

replace_once(
    "import jp.example.greenreader.ar.BackgroundRenderer\n",
    "import jp.example.greenreader.ar.BackgroundRenderer\nimport jp.example.greenreader.field.GrainFieldRecorder\n",
)

replace_once(
    "    @Volatile private var captureRequested = false\n",
    "    @Volatile private var captureRequested = false\n    @Volatile private var autoGrainSavePending = false\n",
)

replace_once(
    """            captureRequested = false
            scanStartMs = SystemClock.elapsedRealtime()
            scanning = true""",
    """            captureRequested = false
            autoGrainSavePending = true
            scanStartMs = SystemClock.elapsedRealtime()
            scanning = true""",
)

replace_once(
    """                val bitmap = captureGlFrame(viewportW, viewportH)
                val projectedBall = ball?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = cup?.let { projectWorldPoint(f.camera, it) }
                capturedBitmap?.recycle()
                capturedBitmap = bitmap
                capturedBallScreen = projectedBall
                capturedCupScreen = projectedCup
                captureRequested = false
                runOnUiThread { analyze(updateStatus = true, showResult = true) }""",
    """                val bitmap = captureGlFrame(viewportW, viewportH)
                val projectedBall = ball?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = cup?.let { projectWorldPoint(f.camera, it) }

                if (autoGrainSavePending) {
                    autoGrainSavePending = false
                    val grainReport = GrainEstimator.estimate(f)
                    if (grainReport != null) {
                        val pose = f.camera.displayOrientedPose
                        val t = FloatArray(3).also { pose.getTranslation(it, 0) }
                        val q = FloatArray(4).also { pose.getRotationQuaternion(it, 0) }
                        grain = grainReport
                        Thread {
                            try {
                                GrainFieldRecorder.save(this, bitmap, grainReport, t, q)
                            } catch (_: Throwable) {
                                // Automatic field logging must never block putting analysis.
                            }
                        }.start()
                    }
                }

                capturedBitmap?.recycle()
                capturedBitmap = bitmap
                capturedBallScreen = projectedBall
                capturedCupScreen = projectedCup
                captureRequested = false
                runOnUiThread { analyze(updateStatus = true, showResult = true) }""",
)

replace_once(
    """        captureRequested = false
        pendingMark = null""",
    """        captureRequested = false
        autoGrainSavePending = false
        pendingMark = null""",
)

path.write_text(s, encoding="utf-8")
print("Enabled automatic grain field logging during normal scan")
