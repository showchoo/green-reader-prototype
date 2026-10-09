"""Offline generated-source regression checks for the M07 v10.1 field issues."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
c=(root/"precision/PrecisionDepthCollector.kt").read_text()
p=(root/"precision/PrecisionFullDepthSupplementPolicy.kt").read_text()
f=(root/"precision/PrecisionDepthFreshnessPolicy.kt").read_text()
m=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
assert 'versionName = "10.1"' in g and 'versionCode = 1010' in g
assert 'appVersion = "Precision 10.1"' in m
assert "PrecisionDepthFreshnessPolicy.evaluate(frame.timestamp, timestamp)" in c
assert 'if (!freshness.acceptable)' in c
assert 'staleRawDepthFrames++' in c and 'staleFullDepthFrames++' in c
assert "MAX_ABS_AGE_NS: Long = 250_000_000L" in f
assert "staleRawDepthFrames = items.sumOf { it.staleRawDepthFrames }" in c
assert "acquiredRawPointCount = items.sumOf { it.acquiredRawPointCount }" in c
assert "acquiredFullPointCount = items.sumOf { it.acquiredFullPointCount }" in c
assert 'depthAcquisitionTotals.acquiredRawPointCount' in m
assert 'depthAcquisitionTotals.acquiredFullPointCount' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'fullPoints.toLong() > 2L * rawPoints.toLong()' in p
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m
assert 'button("結果入力")' in m
print("v10.1: timestamp freshness, original source counts and safety invariants PASS")
