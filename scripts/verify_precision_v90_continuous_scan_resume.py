"""Regression proof that a second scan resumes ARCore before checking tracking."""
from pathlib import Path
s=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "9.0"' in g and 'versionCode = 900' in g
assert 'appVersion = "Precision 9.0"' in s
scan=s[s.index("    private fun toggleScan() {"):s.index("    private fun requestCaptureAndAnalyze(")]
assert scan.index("showCamera()") < scan.index("PrecisionTrackingRetryPolicy.choose(")
assert scan.index("restartRenderLoop()") < scan.index("PrecisionTrackingRetryPolicy.choose(")
assert scan.index("PrecisionTrackingRetryPolicy.choose(") < scan.index("precisionScanIndex += 1")
assert "schedulePrecisionScanTrackingResume()" in scan
assert "precisionScanRetryGeneration += 1" in scan
assert "beginNextPrecisionPutt()" in scan
helper=s[s.index("    private fun schedulePrecisionScanTrackingResume() {"):s.index("    private fun toggleScan() {")]
assert "SystemClock.elapsedRealtime() + 10000L" in helper
assert "scanButton.postDelayed({ retry() }, 250L)" in helper
assert "precisionPuttId != expectedPutt" in helper
assert "ballAnchor !== expectedBall || cupAnchor !== expectedCup" in helper
assert "if (generation != precisionScanRetryGeneration" in helper
assert "PrecisionRepeatScanRecovery.Decision.WAIT" in helper
assert "PrecisionRepeatScanRecovery.Decision.REMARK" in helper
assert "PrecisionRepeatScanRecovery.Decision.TIMEOUT" in helper
for marker in ("private fun beginNextPrecisionPutt()", "private fun redoPrecisionMarkers(onlyCup: Boolean)",
               "private fun resetAll()", "override fun onPause()"):
    block=s[s.index(marker):s.index(marker)+250]
    assert "precisionScanRetryGeneration += 1" in block,marker
assert "requestCaptureAndAnalyze(" in s and "recordPrecisionScanFailure(retryMessage)" in s
assert "PrecisionScaleDirectionAudit.evaluate(" in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert 'button("次のパット")' in s and 'button("次のホール")' in s
assert 'button("結果入力")' in s
assert "precisionFramePoseScanSummary()" in s
print("v9.0 AR camera resume / queued 2nd scan safeguards PASS")
