"""Regression guard for the generated Green Reader Precision v7.0 source."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")
collector = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionDepthCollector.kt").read_text(encoding="utf-8")
recorder = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt").read_text(encoding="utf-8")
quality = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionQualityEstimator.kt").read_text(encoding="utf-8")
tracking = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionTrackingMonitor.kt").read_text(encoding="utf-8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")

assert 'versionName = "7.0"' in gradle and 'versionCode = 700' in gradle
assert 'appVersion = "Precision 7.0"' in main

assert "precisionFieldSessionId" in main
assert "precisionPuttId = 1" in main
assert "precisionScanIndex += 1" in main
assert "ScanFieldRecorder.RecordIdentity(" in main
assert 'button("次のパット")' in main
assert "beginNextPrecisionPutt()" in main
assert "finalPrecisionRecordIdentity()" in main

assert "ScanFieldRecorder.saveGrouped(" in main
assert "ScanFieldRecorder.saveFailureGrouped(" in main
assert "fun saveGrouped(" in recorder
assert "fun saveFailureGrouped(" in recorder
assert 'return "Session_$session/$putt/${scan}_$stamp"' in recorder
assert '"schema_version": 3' in recorder
assert "record_identity.json" in recorder
assert "scan_quality.json" in recorder
assert "Build.MANUFACTURER" in recorder
assert "\"arcore_depth_supported\"" in recorder

assert "lastRawDepthTimestamp" in collector
assert "lastFullDepthTimestamp" in collector
assert "duplicateRawFrames" in collector
assert "duplicateFullFrames" in collector
assert "fun diagnosticSnapshot()" in collector
assert "data class DiagnosticsSnapshot" in collector

assert "PrecisionQualityEstimator.evaluate(" in main
assert "precisionCollectorWindowSnapshots += precisionCollector.diagnosticSnapshot()" in main
assert "precisionTrackingMonitor.observe(" in main
assert "estimatedSlopeUncertaintyPercent" in quality
assert 'TIER_HIGH_PRECISION = "HIGH_PRECISION"' in quality
assert 'TIER_STANDARD = "STANDARD"' in quality
assert 'TIER_LOW_CONFIDENCE = "LOW_CONFIDENCE"' in quality
assert "medianLocalRmseMm" in quality
assert "windowCrossStdDevPercent" in quality
assert "poseJumpCount" in tracking
assert "cameraTravelMeters" in tracking

analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf-8")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in analyzer
assert "MAX_LOCAL_RMSE_METERS = 0.040" in analyzer
assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer
assert "val precisionMinWindows = 5" in main
assert "val precisionMaxWindows = 8" in main
assert "precisionWindowElapsedMs < 1200L" in main

print("Precision v7.0 regression checks passed")
