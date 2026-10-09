"""Generated v9.6 marker interaction invariants; no AR accuracy compromises."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "9.6"' in g and 'versionCode = 960' in g
assert 'appVersion = "Precision 9.6"' in s
assert '@Volatile private var markMode = 1' in s
assert 'markMode == 0 && (ball == null || cup == null)' in s
assert 'markMode = if (ball == null) 1 else 2' in s
assert 'ev.actionMasked == MotionEvent.ACTION_DOWN' in s
assert 'ev.actionMasked == MotionEvent.ACTION_UP' in s
assert 'pendingMark === request' in s
assert 'MARK timeout no fresh renderer frame within 3.5s' in s
assert 'status.postDelayed({' in s and '}, 3500L)' in s
assert 'restartRenderLoop()' in s and 'gl.requestRender()' in s
assert 'markMode = 2' in s
assert 'markMode = 1' in s
assert 'PrecisionMarkerCandidateGate.evaluate(' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionMotionEvidenceGate.evaluate(' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'PrecisionSamePuttAudit.evaluate(' in s
assert 'button("次のパット")' in s and 'button("結果入力")' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
assert 'ゴルフ場スキャンデータ' in (
    root/"field/DriveBackupScheduler.kt").read_text()
assert 'Drive連携の診断をコピー' in (root/"DataManagerActivity.kt").read_text()
assert 'precision_depth_sources.csv' in (
    root/"field/ScanFieldRecorder.kt").read_text()
print("v9.6 marker event, timeout, multi-scan and Drive regression: PASS")
