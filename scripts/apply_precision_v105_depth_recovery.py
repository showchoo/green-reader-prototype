"""v10.5: distinguish repeated Raw+Full unavailable from slope fit failure.

A full ARCore Session recreation invalidates ball/cup anchors. Do NOT restart
automatically. On the second complete no-depth scan offer an explicit dialog
with one-tap session recreation, preserving earlier saved log files.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(x,old,new,label):
    count=x.count(old)
    if count!=1:
        raise RuntimeError(f"v10.5 {label}: expected 1; found {count}")
    return x.replace(old,new,1)

m=one(m,
'''    private val precisionFramePoseWindows = ArrayList<String>(8)''',
'''    private val precisionFramePoseWindows = ArrayList<String>(8)
    private var precisionConsecutiveNoDepthScans = 0
    private var precisionDepthRestartPromptShown = false''',
"persistent per-session no-Depth history")

m=one(m,
'''        precisionLastDiagnostic += " | " + depthHealth.diagnostic()
        if (combined != null) {''',
'''        precisionLastDiagnostic += " | " + depthHealth.diagnostic()

        // Count only TERMINAL scans; intermediate windows must not be counted
        // as separate user attempts. Tracking and Depth availability are
        // independent signals on S20+. Preserve failed scan field logs.
        val finalDepthDecision =
            combined != null || depthHealth.abortEarly ||
                consensusWindowIndex >= precisionMaxWindows
        val depthRecovery = jp.example.greenreader.precision.PrecisionDepthRecoveryAdvisor
            .evaluate(precisionConsecutiveNoDepthScans,
                depthHealth.state,finalDepthDecision)
        precisionConsecutiveNoDepthScans=depthRecovery.consecutiveNoDepthScans
        if (finalDepthDecision && precisionConsecutiveNoDepthScans == 0) {
            precisionDepthRestartPromptShown=false
        }
        precisionLastDiagnostic += " | " + depthRecovery.diagnostic()
        if (depthRecovery.offerRestart && !precisionDepthRestartPromptShown) {
            val expectedPutt=precisionPuttId
            scanButton.postDelayed({
                if (activityActive && !scanning && session != null &&
                    precisionPuttId == expectedPutt &&
                    !precisionDepthRestartPromptShown) {
                    precisionDepthRestartPromptShown=true
                    android.app.AlertDialog.Builder(this)
                        .setTitle("Depth画像が連続して取得できません")
                        .setMessage(
                            "2回以上の測定でRaw・Full両方のDepth画像を取得できませんでした。" +
                            "ARの追跡はできていてもDepthだけ停止する場合があります。\\\\n\\\\n" +
                            "AR・Depthを再起動すると保存済みログは残りますが、" +
                            "現在のボール・カップ位置は再指定が必要です。"
                        )
                        .setNegativeButton("あとで",null)
                        .setPositiveButton("AR・Depth再起動") { _, _ ->
                            if (!scanning) {
                                precisionScanRetryGeneration += 1
                                getSharedPreferences("precision_diagnostics",MODE_PRIVATE)
                                    .edit().putLong(
                                        "depth_restart_requested_at",
                                        System.currentTimeMillis()
                                    ).apply()
                                recreate()
                            }
                        }
                        .show()
                }
            }, 850L)
        }
        if (combined != null) {''',
"one-tap opt-in recovery after consecutive complete scan failures")

# Python triple strings must generate valid Kotlin escaped newlines.
assert 'Depth画像が連続して取得できません' in m
assert 'precisionDepthRestartPromptShown=true' in m
assert 'if (depthRecovery.offerRestart' in m
assert 'precisionScanRetryGeneration += 1' in m
assert 'confirmPrecisionDepthRestart()' in m
assert 'PrecisionDepthStallPolicy.evaluate(' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m
if m.count("Precision 10.4")<2:
    raise RuntimeError("v10.5 expected v10.4 version labels")
m=m.replace("Precision 10.4","Precision 10.5")
g=one(g,'versionName = "10.4"','versionName = "10.5"',"versionName")
g=one(g,'versionCode = 1040','versionCode = 1050',"versionCode")

main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v10.5 consecutive depth-stall consent dialog (never auto-restart)")
