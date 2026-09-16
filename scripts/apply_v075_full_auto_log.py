from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.7.5 pattern not found:\n{old[:500]}")
    s = s.replace(old, new, 1)

replace_once(
    "import jp.example.greenreader.field.GrainFieldRecorder\n",
    "import jp.example.greenreader.field.GrainFieldRecorder\nimport jp.example.greenreader.field.ScanFieldRecorder\n",
)

replace_once(
    "    @Volatile private var autoGrainSavePending = false\n",
    """    @Volatile private var autoGrainSavePending = false
    @Volatile private var autoScanLogPending = false
    private var capturedCameraTranslation = floatArrayOf(0f, 0f, 0f)
    private var capturedCameraQuaternion = floatArrayOf(0f, 0f, 0f, 1f)
    private var capturedGrain: GrainReport? = null
""",
)

replace_once(
    """            autoGrainSavePending = true
            scanStartMs = SystemClock.elapsedRealtime()""",
    """            autoGrainSavePending = true
            autoScanLogPending = true
            scanStartMs = SystemClock.elapsedRealtime()""",
)

old_grain_block = """                if (autoGrainSavePending) {
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
"""
new_grain_block = """                if (autoGrainSavePending) {
                    autoGrainSavePending = false
                    val pose = f.camera.displayOrientedPose
                    capturedCameraTranslation = FloatArray(3).also { pose.getTranslation(it, 0) }
                    capturedCameraQuaternion = FloatArray(4).also { pose.getRotationQuaternion(it, 0) }
                    capturedGrain = GrainEstimator.estimate(f)
                    capturedGrain?.let { grain = it }
                }
"""
replace_once(old_grain_block, new_grain_block)

anchor = """        val image = capturedBitmap
        val bp = capturedBallScreen
        val cp = capturedCupScreen
        if (image != null && bp != null && cp != null) {
            overlayView.setResult(image, bp, cp, report, adv)
        } else if (!updateStatus && overlayView.report != null) {
            overlayView.updateAdvice(adv)
        }
"""
insert = anchor + """
        if (autoScanLogPending && image != null) {
            autoScanLogPending = false
            val pointsForLog = collector.snapshot()
            val bitmapForLog = image.copy(Bitmap.Config.ARGB_8888, false)
            val grainForLog = capturedGrain ?: grain
            val meta = ScanFieldRecorder.CaptureMeta(
                appVersion = "0.7.7",
                trackingState = trackingStateText,
                viewportWidth = viewportW,
                viewportHeight = viewportH,
                cameraTranslation = capturedCameraTranslation.copyOf(),
                cameraQuaternion = capturedCameraQuaternion.copyOf(),
                ballScreenX = bp?.x,
                ballScreenY = bp?.y,
                cupScreenX = cp?.x,
                cupScreenY = cp?.y
            )
            Thread {
                try {
                    ScanFieldRecorder.save(
                        this,
                        bitmapForLog,
                        pointsForLog,
                        b,
                        c,
                        report,
                        adv,
                        grainForLog,
                        meta
                    )
                } catch (_: Throwable) {
                    // Field logging is best-effort and must never block putting analysis.
                } finally {
                    bitmapForLog.recycle()
                }
            }.start()
        }
"""
replace_once(anchor, insert)

replace_once(
    """        autoGrainSavePending = false
        pendingMark = null""",
    """        autoGrainSavePending = false
        autoScanLogPending = false
        capturedGrain = null
        capturedCameraTranslation = floatArrayOf(0f, 0f, 0f)
        capturedCameraQuaternion = floatArrayOf(0f, 0f, 0f, 1f)
        pendingMark = null""",
)

path.write_text(s, encoding="utf-8")
print("Enabled complete automatic scan logging")
