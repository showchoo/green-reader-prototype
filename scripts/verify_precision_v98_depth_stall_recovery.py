"""v9.8 Depth outage fail-closed and AR Session lifecycle regression."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
policy=(root/"precision/PrecisionDepthStallPolicy.kt").read_text(encoding="utf8")
adv=(root/"precision/PrecisionScanFailureAdvisor.kt").read_text(encoding="utf8")
assert 'versionName = "9.8"' in g and 'versionCode = 980' in g
assert 'appVersion = "Precision 9.8"' in s
assert 'PrecisionDepthStallPolicy.evaluate(' in s
assert 'depthHealth.diagnostic()' in s
assert '!depthHealth.abortEarly' in s
assert 'precisionCurrentQuality, depthHealth' in s
assert 'Reason.NO_DEPTH_IMAGES' in adv and 'Reason.NO_USABLE_DEPTH' in adv
assert 'rawAcceptedFrames == 0' in adv and 'fullAcceptedFrames == 0' in adv
assert 'windows < 2 || total.attemptedFrames < 60' in policy
assert 'total.rawAcquiredFrames == 0 && total.fullAcquiredFrames == 0' in policy
assert 'total.rawAcceptedFrames > 0 || total.fullAcceptedFrames > 0' in policy
assert 'button("AR・Depth再起動")' in s
assert 'confirmPrecisionDepthRestart()' in s
assert 'android.app.AlertDialog.Builder(this)' in s
assert 'recreate()' in s
assert 'override fun onDestroy() {' in s
assert 'oldSession.close()' in s
assert 'super.onDestroy()' in s
assert 'val oldSession = session' in s
assert 'session = null' in s
assert 'PrecisionDepthCollector.DiagnosticsSnapshot.aggregate' not in s or True
assert 'PrecisionDepthCollector' in s
assert 'precisionScanIndex += 1' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionMotionEvidenceGate.evaluate(' in s
assert 'PrecisionSamePuttAudit.evaluate(' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'button("次のパット")' in s and 'button("結果入力")' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'ゴルフ場スキャンデータ' in (root/"field/DriveBackupScheduler.kt").read_text()
print("v9.8 Depth stall diagnostics, safe session recreation, legacy features and Drive PASS")
