"""v9.0: resume paused AR result view BEFORE second-scan tracking preflight.

After scan results, showMap()/showOverlay() hides GLSurfaceView and pauses
ARCore. v8.9 checks the cached trackingStateText before showCamera(), so
it sees PAUSED and returns, leaving ARCore suspended indefinitely.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
path=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
s=path.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(old,new,tag):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v9.0 {tag} expected once but found {s.count(old)}")
    s=s.replace(old,new,1)

one(
'''    private fun toggleScan() {
        if (scanning) return
        if (ball == null || cup == null) {
            status.text = if (ball == null) "ボールをタップしてください" else "カップをタップしてください"
            return
        }
        val retryAction =''',
'''    private fun toggleScan() {
        if (scanning) return
        if (ball == null || cup == null) {
            status.text = if (ball == null) "ボールをタップしてください" else "カップをタップしてください"
            return
        }
        // A successful scan displays a result that SUSPENDS ARCore and hides
        // the GLSurfaceView. Resume FIRST, then let new camera frames arrive.
        // Checking cached trackingStateText before this would deadlock every
        // second SCAN after showing a result (the v8.9 bug).
        showCamera()
        restartRenderLoop()
        val retryAction =''',
"camera must resume before tracking preflight")

one(
'''                else -> {
                    status.text =
                        jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.instruction(retryAction)
                }
            }
            return
        }

        pendingMark = null
        showCamera()
''',
'''                else -> {
                    status.text = "カメラを再開しました。位置追跡の復帰を確認しています…"
                    schedulePrecisionScanTrackingResume()
                }
            }
            return
        }

        // The pending retry is now superseded by this real scan.
        precisionScanRetryGeneration += 1
        pendingMark = null
''',
"auto-retry after reopening camera")

helper=r'''    // Retry only after the user deliberately pressed SCAN. Do not fabricate
    // success, and do not start a scan if a putt or AR anchor has changed.
    private var precisionScanRetryGeneration: Int = 0

    private fun schedulePrecisionScanTrackingResume() {
        val generation = ++precisionScanRetryGeneration
        val expectedPutt = precisionPuttId
        val expectedBall = ballAnchor
        val expectedCup = cupAnchor
        val expiresAt = SystemClock.elapsedRealtime() + 10000L

        fun retry() {
            if (generation != precisionScanRetryGeneration ||
                !activityActive || scanning || precisionPuttId != expectedPutt ||
                ballAnchor !== expectedBall || cupAnchor !== expectedCup) return
            val action = jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.choose(
                trackingStateText == TrackingState.TRACKING.name,
                ballAnchor?.trackingState?.name,
                cupAnchor?.trackingState?.name
            )
            val decision = jp.example.greenreader.precision.PrecisionRepeatScanRecovery.decide(
                action,
                SystemClock.elapsedRealtime() >= expiresAt
            )
            when (decision) {
                jp.example.greenreader.precision.PrecisionRepeatScanRecovery.Decision.START -> {
                    precisionScanRetryGeneration += 1
                    toggleScan()
                }
                jp.example.greenreader.precision.PrecisionRepeatScanRecovery.Decision.WAIT -> {
                    scanButton.postDelayed({ retry() }, 250L)
                }
                jp.example.greenreader.precision.PrecisionRepeatScanRecovery.Decision.REMARK -> {
                    precisionScanRetryGeneration += 1
                    status.text = jp.example.greenreader.precision.PrecisionTrackingRetryPolicy
                        .instruction(action) + "。位置を再指定してください"
                }
                jp.example.greenreader.precision.PrecisionRepeatScanRecovery.Decision.TIMEOUT -> {
                    precisionScanRetryGeneration += 1
                    status.text = "位置追跡が10秒間復帰しませんでした。画面に床面を映し、もう一度スキャンしてください"
                }
            }
        }
        scanButton.postDelayed({ retry() }, 250L)
    }

'''
marker="    private fun toggleScan() {\n"
one(marker,helper+marker,"retry helper location")

# Changing position/putt and leaving the activity must cancel stale retry.
one(
'''    private fun beginNextPrecisionPutt() {
        if (scanning) {''',
'''    private fun beginNextPrecisionPutt() {
        precisionScanRetryGeneration += 1
        if (scanning) {''',
"cancel pending next putt")
one(
'''    private fun redoPrecisionMarkers(onlyCup: Boolean) {
        if (scanning) {''',
'''    private fun redoPrecisionMarkers(onlyCup: Boolean) {
        precisionScanRetryGeneration += 1
        if (scanning) {''',
"cancel pending re-mark")
one(
'''    private fun resetAll() {
        scanning = false''',
'''    private fun resetAll() {
        precisionScanRetryGeneration += 1
        scanning = false''',
"cancel pending reset")
one(
'''    override fun onPause() {
        super.onPause()
        activityActive = false''',
'''    override fun onPause() {
        super.onPause()
        precisionScanRetryGeneration += 1
        activityActive = false''',
"cancel pending pause")

if s.count('appVersion = "Precision 8.9"')<2:
    raise SystemExit("Expected v8.9 app version")
s=s.replace('Precision 8.9','Precision 9.0')
if g.count('versionName = "8.9"')!=1 or g.count('versionCode = 890')!=1:
    raise SystemExit("Expected v8.9 Gradle version")
g=g.replace('versionName = "8.9"','versionName = "9.0"')
g=g.replace('versionCode = 890','versionCode = 900')
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'recordPrecisionScanFailure(retryMessage)' in s
path.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v9.0: camera resumed before tracking preflight; 10s guarded queued scan")
