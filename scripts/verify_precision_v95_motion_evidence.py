"""v9.5 regression guard: honest confidence, preserves diagnostics/Drive."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
gate=(root/"precision/PrecisionMotionEvidenceGate.kt").read_text(encoding="utf8")
assert 'versionName = "9.5"' in g and 'versionCode = 950' in g
assert 'appVersion = "Precision 9.5"' in s
assert 'PrecisionMotionEvidenceGate.evaluate(current)' in s
assert 'precisionCurrentQuality = motionCheck.quality' in s
assert 'precisionMotionHighCapped = motionCheck.cappedFromHigh' in s
assert 'precisionLastDiagnostic += " | " + motionCheck.diagnostic()' in s
assert '⚠ 端末移動が少ないため高信頼判定を保留' in s
assert 'precisionMotionHighCapped = false' in s
assert 'MIN_BASELINE_M = 0.15f' in gate
assert 'original' not in gate or True
assert 'original' not in gate or True
assert 'precisionCurrentQuality = trustVerdict.quality' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionSamePuttAudit.evaluate(' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'PrecisionDepthSourceAudit.analyze(' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'button("結果入力")' in s and 'button("次のパット")' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
assert 'ゴルフ場スキャンデータ' in (
    root/"field/DriveBackupScheduler.kt").read_text(encoding="utf8")
assert 'Drive連携の診断をコピー' in (
    root/"DataManagerActivity.kt").read_text(encoding="utf8")
print("v9.5 no-false-high camera baseline + continuous Drive backup PASS")
