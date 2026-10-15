"""Verify v10.4 generated projection ray audit with fail-closed safety intact."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
c=(root/"precision/PrecisionDepthCollector.kt").read_text()
m=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
a=(root/"precision/PrecisionProjectionRayAudit.kt").read_text()
t=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionProjectionRayAuditTest.kt").read_text()
assert 'versionName = "10.4"' in g and 'versionCode = 1040' in g
assert 'appVersion = "Precision 10.4"' in m
assert 'projectionRayAudit = PrecisionProjectionRayAudit.Buffer()' in c
assert 'projectionRayAudit.clear()' in c
assert 'projectionRayAudit.diagnostic()' in c
assert 'observeProjectionRayAudit(' in c
assert 'frame.transformCoordinates2d(' in c
assert 'Coordinates2d.TEXTURE_NORMALIZED' in c
assert 'Coordinates2d.IMAGE_PIXELS' in c
assert 'PrecisionProjectionRayAudit.cameraRay(' in c
assert 'PROJECTION_RAY_AUDIT_V1' in a
assert 'diagnosticOnly=true groundTruth=false' in a
assert 'fun cameraRay(' in a
assert 'cameraRayYSignAndScalingAreCorrect' in t
assert 'independentRawAndFullDiagnosticsNeverImplyGroundTruth' in t
assert 'PrecisionGroundPlaneBiasAudit.diagnostic(' in c
assert 'PrecisionSourceOverlapAudit.diagnostic(samples)' in c
assert 'PrecisionDepthFreshnessPolicy.evaluate(frame.timestamp, timestamp)' in c
assert 'rawConfidenceHistogram[conf ushr 5]++' in c
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m
print("v10.4: dual projection rays and all production safety invariants PASS")
