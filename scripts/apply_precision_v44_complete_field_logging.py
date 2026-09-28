"""v6.4: automatic field packages for successful and failed Precision scans."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.4 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

once(
'''    private var precisionLastDiagnostic: String = ""
    private val precisionWindowDiagnostics = ArrayList<String>(8)
''',
'''    private var precisionLastDiagnostic: String = ""
    private val precisionWindowDiagnostics = ArrayList<String>(8)
    private var precisionFailureRecordSaved = false
    private var latestCameraTranslation = floatArrayOf(0f, 0f, 0f)
    private var latestCameraQuaternion = floatArrayOf(0f, 0f, 0f, 1f)
''',
"field record state"
)

# Capture the latest camera pose continuously; this is cheap and lets failed
# scans keep enough pose context without forcing an extra framebuffer capture.
once(
'''            latestFrame = f
            trackingStateText = f.camera.trackingState.name
''',
'''            latestFrame = f
            trackingStateText = f.camera.trackingState.name
            val latestPose = f.camera.displayOrientedPose
            latestCameraTranslation = FloatArray(3).also { latestPose.getTranslation(it, 0) }
            latestCameraQuaternion = FloatArray(4).also { latestPose.getRotationQuaternion(it, 0) }
''',
"latest camera pose"
)

# Every new scan owns exactly one failure package at most.
once(
'''        autoGrainSavePending = true
        autoScanLogPending = true
        scanning = true
''',
'''        autoGrainSavePending = true
        autoScanLogPending = true
        precisionFailureRecordSaved = false
        scanning = true
''',
"scan record reset"
)

# Persist failed scans automatically. No user interaction is needed.
old_failure='''    private fun recordPrecisionScanFailure(message: String) {
        val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
        val full = message + "\n\n" + detail
        getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
            .edit()
            .putString("last_failure", full)
            .putLong("last_failure_time", System.currentTimeMillis())
            .apply()
        status.text = message + "（診断保存済み）"
        Toast.makeText(this, "再スキャンできます", Toast.LENGTH_SHORT).show()
    }
'''
new_failure='''    private fun recordPrecisionScanFailure(message: String) {
        val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
        val full = message + "\n\n" + detail
        val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
        prefs.edit()
            .putString("last_failure", full)
            .putLong("last_failure_time", System.currentTimeMillis())
            .apply()

        if (!precisionFailureRecordSaved) {
            precisionFailureRecordSaved = true
            val precisionPointsForLog =
                if (precisionLogPoints.isNotEmpty()) precisionLogPoints.toList()
                else precisionCollector.snapshot()
            val markerDiagnostic = prefs.getString("last_marker", "") ?: ""
            val collectorDiagnostic = precisionCollector.diagnosticSummary()
            val ballForLog = ball
            val cupForLog = cup
            val meta = ScanFieldRecorder.CaptureMeta(
                appVersion = "Precision 6.4",
                trackingState = trackingStateText,
                viewportWidth = viewportW,
                viewportHeight = viewportH,
                cameraTranslation = latestCameraTranslation.copyOf(),
                cameraQuaternion = latestCameraQuaternion.copyOf(),
                ballScreenX = null,
                ballScreenY = null,
                cupScreenX = null,
                cupScreenY = null
            )
            Thread {
                try {
                    ScanFieldRecorder.saveFailure(
                        this,
                        precisionPointsForLog,
                        ballForLog,
                        cupForLog,
                        message,
                        detail,
                        markerDiagnostic,
                        collectorDiagnostic,
                        meta
                    )
                } catch (_: Throwable) {
                    // Logging must never block another field attempt.
                }
            }.start()
        }

        status.text = message + "（自動保存済み）"
        Toast.makeText(this, "再スキャンできます", Toast.LENGTH_SHORT).show()
    }
'''
once(old_failure,new_failure,"automatic failure package")

# Successful scans keep the legacy package and add the full Precision dataset.
old_success='''                    ScanFieldRecorder.save(
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
'''
new_success='''                    val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
                    ScanFieldRecorder.save(
                        this,
                        bitmapForLog,
                        pointsForLog,
                        b,
                        c,
                        report,
                        adv,
                        grainForLog,
                        meta,
                        precisionPoints = precisionLogPoints.toList(),
                        precisionDiagnostic = precisionLastDiagnostic,
                        markerDiagnostic = prefs.getString("last_marker", "") ?: "",
                        collectorDiagnostic = precisionCollector.diagnosticSummary()
                    )
'''
once(old_success,new_success,"successful precision package")

# The existing generated success metadata had a literal v6.3.
if s.count('appVersion = "Precision 6.3"') != 1:
    raise SystemExit("v6.4 success metadata version target missing")
s=s.replace('appVersion = "Precision 6.3"','appVersion = "Precision 6.4"',1)

if s.count('appVersion = "Precision 6.3"') != 0:
    raise SystemExit("stale Precision 6.3 metadata remains")

# Main visible version / Gradle version.
if s.count('appVersion = "Precision 6.3"') != 0:
    raise SystemExit("unexpected duplicate version")
# v6.3 version marker lives in the visible version string after previous patches.
if 'Precision 6.3' in s:
    s=s.replace('Precision 6.3','Precision 6.4')

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.3"') != 1 or g.count('versionCode = 630') != 1:
    raise SystemExit("v6.4 gradle version target missing")
g=g.replace('versionName = "6.3"','versionName = "6.4"',1)
g=g.replace('versionCode = 630','versionCode = 640',1)

assert "ScanFieldRecorder.saveFailure(" in s
assert "precisionPoints = precisionLogPoints.toList()" in s
assert "precisionDiagnostic = precisionLastDiagnostic" in s
assert "collectorDiagnostic = precisionCollector.diagnosticSummary()" in s
assert 'status.text = message + "（自動保存済み）"' in s

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.4 complete automatic field logging")
