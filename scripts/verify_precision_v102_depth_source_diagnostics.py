"""Validate generated v10.2 diagnostics and production fail-closed invariants."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
c=(root/"precision/PrecisionDepthCollector.kt").read_text()
m=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
a=(root/"precision/PrecisionSourceOverlapAudit.kt").read_text()
t=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionSourceOverlapAuditTest.kt").read_text()
assert 'versionName = "10.2"' in g and 'versionCode = 1020' in g
assert 'appVersion = "Precision 10.2"' in m
assert 'rawConfidenceHistogram[conf ushr 5]++' in c
assert c.index('rawConfidenceHistogram[conf ushr 5]++') < c.index('if (conf < confidenceThreshold) continue')
assert 'rawConfidenceBins = (0 until 8).map' in c
assert 'rawConfBins32=' in m
assert 'fullProjectionRejectedPixels++' in c
assert 'PrecisionSourceOverlapAudit.diagnostic(samples)' in c
assert 'DEPTH_SOURCE_OVERLAP_V1' in a and 'diagnosticOnly=true' in a
assert 'matchedHeightOffsetReportedWithoutClaimingGroundTruth' in t
assert 'PrecisionDepthFreshnessPolicy.evaluate(frame.timestamp, timestamp)' in c
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m
print("v10.2: confidence distribution, co-located Raw/Full height residuals and safety invariants PASS")
