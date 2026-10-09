"""v9.8: detect actual Depth image starvation; provide safe one-tap recovery.

ARCore may remain TRACKING while neither Raw nor Full Depth is available.
A fresh Session invalidates physical marker anchors, so re-mark instead
of silently assuming they still refer to the same physical points.
Never turn unavailable measurements into valid slopes.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
path=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
s=path.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
def one(a,b,name):
    global s
    c=s.count(a)
    if c!=1: raise SystemExit("v9.8 " + name + " expected 1 found " + str(c))
    s=s.replace(a,b,1)

one('''        if (combined != null) {
            precisionCompletedDiagnostic = precisionLastDiagnostic
        }

        if (combined == null && consensusWindowIndex < precisionMaxWindows) {''',
'''        // ARCore camera TRACKING is independent of the Depth API. Detect
        // persistent missing Raw AND Full image evidence without waiting for
        // all eight collection windows, while retaining every failed scan.
        val depthHealth =
            jp.example.greenreader.precision.PrecisionDepthStallPolicy.evaluate(
                jp.example.greenreader.precision.PrecisionDepthCollector
                    .DiagnosticsSnapshot.aggregate(precisionCollectorWindowSnapshots),
                precisionCollectorWindowSnapshots.size
            )
        precisionLastDiagnostic += " | " + depthHealth.diagnostic()
        if (combined != null) {
            precisionCompletedDiagnostic = precisionLastDiagnostic
        }

        if (combined == null && consensusWindowIndex < precisionMaxWindows &&
            !depthHealth.abortEarly) {''',
"early abort on actual Depth stall")
one('''                    jp.example.greenreader.precision.PrecisionScanFailureAdvisor.evaluate(
                        precisionCurrentQuality
                    )''',
'''                    jp.example.greenreader.precision.PrecisionScanFailureAdvisor.evaluate(
                        precisionCurrentQuality, depthHealth
                    )''',
"accurate cause")

# Add recovery button without removing the user's existing controls.
one('''        panel.addView(expandedMenu)''',
'''        val depthRecoveryRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        depthRecoveryRow.addView(
            button("AR・Depth再起動") { confirmPrecisionDepthRestart() },
            LinearLayout.LayoutParams(-1, dp(42))
        )
        expandedMenu.addView(depthRecoveryRow)
        panel.addView(expandedMenu)''',
"recovery menu")
recovery = '''    /**
     * Explicit user-approved repair. On recreation the old ARCore Session is
     * released and a new one is configured with DepthMode.AUTOMATIC.
     * Existing session/putt/scan files remain in MediaStore + Google Drive.
     * Markers must be placed again: do not reuse anchors across Sessions.
     */
    private fun confirmPrecisionDepthRestart() {
        if (scanning) {
            status.text = "測定中はARを再起動できません。終了後に再試行してください"
            return
        }
        android.app.AlertDialog.Builder(this)
            .setTitle("AR・Depthを再起動")
            .setMessage(
                "Depthが取得できない場合、ARCoreのセッションを作り直します。" +
                "保存済みデータは保持します。ボール・カップは再指定が必要です。"
            )
            .setNegativeButton("キャンセル", null)
            .setPositiveButton("再起動") { _, _ ->
                precisionScanRetryGeneration += 1
                getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
                    .edit().putLong("depth_restart_requested_at", System.currentTimeMillis())
                    .apply()
                recreate()
            }
            .show()
    }

'''
one('''    private fun restartRenderLoop() {''',
recovery+'''    private fun restartRenderLoop() {''',
"recovery UI helper")
# Per Google's ARCore lifecycle contract, explicitly close native resources
# when the old activity is destroyed. A reopened activity creates a fresh
# Session and must not share the previous anchor identity or GL rendering.
one('''    override fun onPause() {
        super.onPause()
        precisionScanRetryGeneration += 1
        activityActive = false
        renderHandler.removeCallbacks(renderTick)
        scanning = false
        pendingMark = null
        if (!arSuspendedForResult) {
            gl.onPause()
            session?.pause()
        }
    }

    override fun onSurfaceCreated(''',
'''    override fun onPause() {
        super.onPause()
        precisionScanRetryGeneration += 1
        activityActive = false
        renderHandler.removeCallbacks(renderTick)
        scanning = false
        pendingMark = null
        if (!arSuspendedForResult) {
            gl.onPause()
            session?.pause()
        }
    }

    override fun onDestroy() {
        renderHandler.removeCallbacks(renderTick)
        precisionScanRetryGeneration += 1
        // onPause() already stopped rendering and paused the camera.
        val oldSession = session
        session = null
        latestFrame = null
        if (oldSession != null) {
            Thread {
                try {
                    oldSession.close()
                } catch (_: Throwable) {
                }
            }.start()
        }
        super.onDestroy()
    }

    override fun onSurfaceCreated(''',
"release native session on activity destruction")

if s.count("Precision 9.7") < 2:raise SystemExit("previous app labels missing")
s=s.replace("Precision 9.7","Precision 9.8")
if g.count('versionName = "9.7"')!=1 or g.count("versionCode = 970")!=1:raise SystemExit("previous Gradle version missing")
g=g.replace('versionName = "9.7"','versionName = "9.8"')
g=g.replace("versionCode = 970","versionCode = 980")
# Guard scientific integrity and valid 3x same-putt scan behavior.
assert 'PrecisionSlopeAnalyzer.analyze(' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionMotionEvidenceGate.evaluate(' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'button("次のパット")' in s
assert 'button("結果入力")' in s
assert 'precisionCurrentQuality' in s
assert 'precisionScanIndex += 1' in s
assert 'val precisionMaxWindows = 8' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
path.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v9.8 bounded Depth stall, honest failure logging, guarded AR recreation + Session.close")
