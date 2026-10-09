"""Safety test for v9.3 Google Drive consent diagnostics."""
from pathlib import Path
s=Path("app/src/main/java/jp/example/greenreader/DataManagerActivity.kt").read_text()
m=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
assert 'versionCode = 930' in g and 'versionName = "9.3"' in g
assert 'appVersion = "Precision 9.3"' in m
assert 'StartIntentSenderForResult()' in s
assert 'driveAuthorizationLauncher.launch(' in s
assert 'IntentSenderRequest.Builder(' in s
assert 'saveDriveAuthDiagnostic(' in s
assert 'Google status=' in s
assert 'OAuth incomplete: resultCode=' in s
assert 'Drive連携の診断をコピー' in s
assert 'last_auth_diagnostic' in s
assert 'getAuthorizationResultFromIntent(data)' in s
assert 'onDriveAuthorizationResult(' in s
assert s.count('override fun onActivityResult(') == 1
assert 'REQ_DRIVE_AUTH' not in s
assert '連携はキャンセルされました' not in s
assert 'ゴルフ場スキャンデータ' in s
assert 'DriveBackupScheduler.setEnabled(this, true)' in s
assert 'DriveBackupScheduler.setEnabled(this, false)' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionRepeatScanRecovery.decide(' in m
assert 'button("次のパット")' in m
print("v9.3 diagnostics and existing Drive sync regression: PASS")
