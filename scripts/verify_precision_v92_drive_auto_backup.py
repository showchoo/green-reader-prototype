"""Static safeguards for v9.2 scoped, opt-in, resumable Drive backup."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
m=(root/"DataManagerActivity.kt").read_text()
r=(root/"field/ScanFieldRecorder.kt").read_text()
sch=(root/"field/DriveBackupScheduler.kt").read_text()
archive=(root/"field/DriveBackupArchive.kt").read_text()
worker=(root/"field/DriveBackupWorker.kt").read_text()
rest=(root/"field/DriveBackupUploader.kt").read_text()
manifest=Path("app/src/main/AndroidManifest.xml").read_text()
assert 'versionName = "9.2"' in g and 'versionCode = 920' in g
assert 'appVersion = "Precision 9.2"' in s
assert 'play-services-auth:21.5.0' in g
assert 'work-runtime-ktx:2.11.2' in g
assert 'android.permission.INTERNET' in manifest
assert sch.count('ゴルフ場スキャンデータ') == 1
assert 'getBoolean("enabled", false)' in sch
assert 'if (isEnabled(context)) enqueue(context)' in sch
assert 'NetworkType.CONNECTED' in sch
assert 'BackoffPolicy.EXPONENTIAL' in sch
assert 'ExistingPeriodicWorkPolicy.KEEP' in sch
assert 'DriveBackupScheduler.onScanSaved(context)' in r
assert r.count('DriveBackupScheduler.onScanSaved(context)') == 4
assert 'saveRecordExtrasModern(context, folder, identity, meta, quality)' in r
assert 'saveFailureGrouped(' in r
assert 'getAuthorizationResultFromIntent(data)' in m
assert m.count('override fun onActivityResult(')==1
assert 'requestDriveAuthorization' not in m
assert 'askGoogleDriveConsent()' in m and 'enableDriveBackup()' in m
assert 'DriveBackupScheduler.setEnabled(this, false)' in m
assert 'https://www.googleapis.com/auth/drive.file' in worker
assert 'https://www.googleapis.com/auth/drive"' not in worker
assert 'if (auth.hasResolution() || auth.accessToken.isNullOrBlank())' in worker
assert 'session.zipName' in worker and 'synced_' in worker
assert 'DriveBackupArchive.sessions' in worker
assert 'Download/GreenReaderRecords/' in archive
assert 'completeScanDirs' in archive
assert 'ZipOutputStream' in archive and 'openInputStream' in archive
assert 'uploadType=resumable' in rest
assert 'X-HTTP-Method-Override' in rest
assert 'firstId(q)' in rest and 'name=' in rest
assert 'Authorization' in rest
# Keep v9.1 scientific diagnostics and v9.0 consecutive scans untouched.
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'PrecisionDepthSourceAudit.analyze(' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'button("次のパット")' in s and 'button("結果入力")' in s
print("v9.2 Drive opt-in, folder, restore, scoped upload safeguards: PASS")
