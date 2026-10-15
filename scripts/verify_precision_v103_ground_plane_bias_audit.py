"""Generated v10.3 gate: diagnostic only; all production safety invariants intact."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
c=(root/"precision/PrecisionDepthCollector.kt").read_text()
m=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
a=(root/"precision/PrecisionGroundPlaneBiasAudit.kt").read_text()
p=(root/"precision/PrecisionARFloorPlaneSampler.kt").read_text()
t=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionGroundPlaneBiasAuditTest.kt").read_text()
assert 'versionName = "10.3"' in g and 'versionCode = 1030' in g
assert 'appVersion = "Precision 10.3"' in m
assert 'private val arFloorPlaneSampler = PrecisionARFloorPlaneSampler()' in c
assert 'arFloorPlaneSampler.clear()' in c
assert 'arFloorPlaneSampler.observe(frame, referencePose)' in c
assert 'PrecisionGroundPlaneBiasAudit.diagnostic(' in c
assert 'PrecisionSourceOverlapAudit.diagnostic(samples)' in c
assert 'rawConfidenceHistogram[conf ushr 5]++' in c
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'GROUND_PLANE_BIAS_V1' in a
assert 'groundTruth=false' in a
assert 'getUpdatedTrackables(Plane::class.java)' in p
assert 'plane.type != Plane.Type.HORIZONTAL_UPWARD_FACING' in p
assert 'diagnosticOnly=true' in a
assert 'tiltedFloorWithClutterStillMeasuresTheDiagnosticTilt' in t
assert 'PrecisionDepthFreshnessPolicy.evaluate(frame.timestamp, timestamp)' in c
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m
print("v10.3 independent plane diagnostic, original fit/quality guard and archive safeguards PASS")
