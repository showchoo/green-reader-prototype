"""Static consistency checks after reconstructing v10.0 from v9.9."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
policy=(root/"precision/PrecisionFullDepthSupplementPolicy.kt").read_text(encoding="utf8")
collector=(root/"precision/PrecisionDepthCollector.kt").read_text(encoding="utf8")
builder=(root/"precision/PrecisionSurfaceBuilder.kt").read_text(encoding="utf8")
selector=(root/"precision/PrecisionAnchoredGroundSelector.kt").read_text(encoding="utf8")
main=(root/"MainActivity.kt").read_text(encoding="utf8")
gradle=Path("app/build.gradle.kts").read_text(encoding="utf8")
test=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionSparseRawFallbackTest.kt").read_text(encoding="utf8")

assert 'versionName = "10.0"' in gradle and 'versionCode = 1000' in gradle
assert 'appVersion = "Precision 10.0"' in main
assert 'const val MIN_RAW_POINTS_PER_FRAME = 160' in policy
assert 'rawPointsInFrame < MIN_RAW_POINTS_PER_FRAME' in policy
assert 'suppressSparseMixedDirection(' in policy
assert 'rawPointsInFrame = rawPointsInFrame' in collector
assert 'sparseRawFrames=' in collector and 'sparseRawFullAcquired=' in collector
assert 'if (isRaw) lastRawAcceptedPointCount = added' in collector
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in main
assert '!sparseMixedUnverified' in main
assert 'precisionDirectionTrustworthy = false' in main
assert 'fieldSparseRawAlwaysRequestsFullEvidence' in test
assert 'longRangeDenseRawStillUsesDistanceLimitedFullSupplement' in test
assert 'PrecisionAnchoredGroundSelector.select(' in builder
assert 'abs(p.height - ball.y) <= .20f' in selector
assert 'NO_NEAR_BALL_GROUND' in selector
assert 'PrecisionSlopeAnalyzer.analyze(' in main
assert 'PrecisionDepthStallPolicy.evaluate(' in main
assert 'PrecisionRepeatScanRecovery.decide(' in main
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in main
assert 'PrecisionMotionEvidenceGate.evaluate(' in main
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in main
assert 'button("結果入力")' in main
print("v10.0: sparse-raw policy, conservative guidance, v9.9 ground rules, scan/Drive retained")
