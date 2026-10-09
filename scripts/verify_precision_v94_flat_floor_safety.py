"""v9.4 compile-time invariants: preserve uploads, truth in quality and line."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
m=(root/"precision/PrecisionMarkerDepthHeightAudit.kt").read_text(encoding="utf8")
q=(root/"precision/PrecisionScanConfidenceGuard.kt").read_text(encoding="utf8")
p=(root/"precision/PrecisionSamePuttAudit.kt").read_text(encoding="utf8")
assert 'versionName = "9.4"' in g and "versionCode = 940" in g
assert 'appVersion = "Precision 9.4"' in s
assert 'val discrepancyLimit = max(.025f, distance * .02f)' in m
assert 'PrecisionSamePuttAudit.evaluate(' in s
assert 'PrecisionScanConfidenceGuard.apply(' in s
assert 'if (trustVerdict.blocksDirection) precisionDirectionTrustworthy = false' in s
assert 'precisionCurrentQuality = trustVerdict.quality' in s
assert 'precisionLastDiagnostic += " | " + samePuttCheck.summary()' in s
assert 'precisionSamePuttSlopeHistory.clear()' in s
assert 'precisionSamePuttSlopesPuttId != precisionPuttId' in s
assert 'precisionSamePuttConflict = false' in s
assert 'if (precisionSamePuttConflict)' in s
assert 'score = original.score.coerceAtMost(59)' in q
assert 'tier = PrecisionQualityEstimator.TIER_LOW_CONFIDENCE' in q
assert 'Status.CONFLICT' in p
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'PrecisionDepthSourceAudit.analyze(' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'button("結果入力")' in s and 'button("次のパット")' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
assert 'ゴルフ場スキャンデータ' in (root/"field/DriveBackupScheduler.kt").read_text()
assert 'Drive連携の診断をコピー' in (root/"DataManagerActivity.kt").read_text()
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
print("v9.4 quality trust, direction veto and Drive continuity checks: PASS")
