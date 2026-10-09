"""v8.9: recover from tracking loss before or during a scan.

Generated v8.8 has *two* guards that used the same error string.
The preflight toggleScan() guard silently rejects untracked anchors, even
when they are permanently STOPPED and cannot possibly resume.
The requestCaptureAndAnalyze() guard returns while the scan button may
still be disabled and scanning=true. This patch makes both paths explicit.
"""
from pathlib import Path

root = Path("app/src/main/java/jp/example/greenreader")
main = root / "MainActivity.kt"
gradle = Path("app/build.gradle.kts")
s = main.read_text(encoding="utf8")
g = gradle.read_text(encoding="utf8")

old = '''        if (ballAnchor?.trackingState != TrackingState.TRACKING ||
            cupAnchor?.trackingState != TrackingState.TRACKING) {
            status.text = "位置追跡を準備中です。端末を少し動かしてから再試行してください"
            return
        }
'''
if s.count(old) != 2:
    raise SystemExit(f"v8.9 expected 2 tracking guards, got {s.count(old)}")

preflight = '''        val retryAction = jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.choose(
            trackingStateText == TrackingState.TRACKING.name,
            ballAnchor?.trackingState?.name,
            cupAnchor?.trackingState?.name
        )
        if (retryAction != jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.READY) {
            // Do not increment scanIndex or silently count a failed preflight.
            // PAUSED can recover; STOPPED anchors never will.
            scanButton.isEnabled = true
            scanButton.text = "▶  SCAN"
            restartRenderLoop()
            when (retryAction) {
                jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.REMARK_BALL,
                jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.REMARK_CUP -> {
                    // A changed AR anchor invalidates same-putt repeatability.
                    // Keep all previous saved data, but start a fresh putt
                    // group if this putt has already attempted any scan.
                    val wasMeasured = precisionScanIndex > 0
                    if (wasMeasured) {
                        beginNextPrecisionPutt()
                    } else {
                        redoPrecisionMarkers(
                            onlyCup = retryAction ==
                                jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.REMARK_CUP
                        )
                    }
                    status.text = (if (wasMeasured) {
                        "位置追跡が失われたため新しいパットを開始しました。"
                    } else "") +
                        "ボールとカップの位置を画面で確認して再指定してください"
                }
                else -> {
                    status.text =
                        jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.instruction(retryAction)
                }
            }
            return
        }
'''
s=s.replace(old,preflight,1)

abort = '''        val captureRetryAction = jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.choose(
            trackingStateText == TrackingState.TRACKING.name,
            ballAnchor?.trackingState?.name,
            cupAnchor?.trackingState?.name
        )
        if (captureRetryAction !=
            jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.READY) {
            // A scan attempt was already recorded: fail it closed, save its
            // diagnostic, and return the SCAN button to an actionable state.
            // Do not change the putt ID until the user starts a new capture.
            scanning = false
            autoStopPending = false
            captureRequested = false
            autoScanLogPending = false
            autoGrainSavePending = false
            pendingMark = null
            scanButton.post {
                scanButton.text = "▶  SCAN"
                scanButton.isEnabled = true
            }
            val retryMessage =
                jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.instruction(captureRetryAction)
            runOnUiThread {
                recordPrecisionScanFailure(retryMessage)
                if (captureRetryAction ==
                    jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.REMARK_BALL ||
                    captureRetryAction ==
                    jp.example.greenreader.precision.PrecisionTrackingRetryPolicy.Action.REMARK_CUP
                ) {
                    status.text = retryMessage + "。「スキャン」を押すと新しいパットで再指定できます"
                }
            }
            return
        }
'''
if s.count(old) != 1:
    raise SystemExit("v8.9 capture-time guard missing")
s=s.replace(old,abort,1)

# Rendering resume should clear the temporary warning, but only if the
# camera AND existing AR anchors have recovered, without touching a scan.
target = '''            latestFrame = f
            val previousTracking = trackingStateText
            trackingStateText = f.camera.trackingState.name
'''
replacement = '''            latestFrame = f
            val previousTracking = trackingStateText
            trackingStateText = f.camera.trackingState.name
            if (!scanning &&
                trackingStateText == TrackingState.TRACKING.name &&
                ballAnchor?.trackingState == TrackingState.TRACKING &&
                cupAnchor?.trackingState == TrackingState.TRACKING
            ) {
                runOnUiThread {
                    if (status.text.toString().startsWith("位置追跡が一時停止")) {
                        status.text = "位置追跡が復帰しました。もう一度スキャンを押してください"
                        scanButton.text = "▶  SCAN"
                        scanButton.isEnabled = true
                    }
                }
            }
'''
if s.count(target)!=1:
    raise SystemExit("v8.9 tracking-recovery rendering hook missing")
s=s.replace(target,replacement,1)

if s.count('appVersion = "Precision 8.8"') < 2:
    raise SystemExit("v8.9 expected existing v8.8 version labels")
s=s.replace('Precision 8.8','Precision 8.9')
if g.count('versionName = "8.8"') != 1 or g.count('versionCode = 880') != 1:
    raise SystemExit("v8.9 Gradle labels mismatch")
g=g.replace('versionName = "8.8"','versionName = "8.9"')
g=g.replace('versionCode = 880','versionCode = 890')
# Preserve critical session semantics.
assert 'precisionScanIndex += 1' in s
assert 'precisionPuttId += 1' in s
assert 'recordPrecisionScanFailure(retryMessage)' in s
assert 'button("次のパット")' in s and 'button("結果入力")' in s
assert 'precisionFramePoseScanSummary()' in s
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v8.9: tracking preflight + capture abort recovery implemented")
