"""v8.9 generated-source guards: never strand an AR scan after tracking loss."""
from pathlib import Path
s=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
p=Path("app/src/main/java/jp/example/greenreader/precision/PrecisionTrackingRetryPolicy.kt").read_text(encoding="utf8")
assert 'versionCode = 890' in g and 'versionName = "8.9"' in g
assert 'appVersion = "Precision 8.9"' in s
assert 'fun choose(cameraTracking: Boolean, ballState: String?, cupState: String?)' in p
assert 'if (ballState == null || ballState == "STOPPED")' in p
assert 'if (cupState == null || cupState == "STOPPED")' in p
assert s.count('PrecisionTrackingRetryPolicy.choose(')==2
assert 'status.text = "位置追跡を準備中です。端末を少し動かしてから再試行してください"' not in s
scan=s[s.index('    private fun toggleScan() {'):s.index('    private fun requestCaptureAndAnalyze(')]
capture=s[s.index('    private fun requestCaptureAndAnalyze('):s.index('    private fun toggleTestMode() {')]
assert scan.index('PrecisionTrackingRetryPolicy.choose(') < scan.index('precisionScanIndex += 1')
assert 'scanButton.isEnabled = true' in scan
assert 'beginNextPrecisionPutt()' in scan
assert 'redoPrecisionMarkers(' in scan
assert 'precisionScanIndex > 0' in scan
assert 'precisionScanIndex += 1' in scan
assert 'scanning = false' in capture and 'captureRequested = false' in capture
assert 'scanButton.isEnabled = true' in capture
assert 'recordPrecisionScanFailure(retryMessage)' in capture
assert 'requestCaptureAndAnalyze(' in s
# prior critical safeguards
assert 'PrecisionScaleDirectionAudit.evaluate(' in s
assert 'PrecisionPairedFlankAudit.evaluate(' in s
assert 'PrecisionDepthSourceAudit.analyze(' in s
assert 'framePoseTelemetry.recordCameraFrame(' in Path(
  "app/src/main/java/jp/example/greenreader/precision/PrecisionDepthCollector.kt").read_text()
assert 'precisionFramePoseScanSummary()' in s
assert 'button("次のパット")' in s and 'button("次のホール")' in s
assert 'button("結果入力")' in s
assert 'button("カップ再指定")' in s
assert 'bitmap = failureBitmap' in s
assert 'metadata.json' in Path(
  "app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt").read_text()
print("v8.9 tracking retry regressions: PASS")
