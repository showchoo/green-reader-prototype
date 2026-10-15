"""Generated v10.5 fail-closed validation for independent slope telemetry and Depth UX."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"precision/PrecisionDepthSourceAudit.kt").read_text()
m=(root/"MainActivity.kt").read_text()
g=Path("app/build.gradle.kts").read_text()
p=(root/"precision/PrecisionDepthRecoveryAdvisor.kt").read_text()
t=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionIndependentSourceSlopeTest.kt").read_text()
r=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionDepthRecoveryAdvisorTest.kt").read_text()
assert 'versionName = "10.5"' in g and 'versionCode = 1050' in g
assert 'appVersion = "Precision 10.5"' in m
assert 'INDEPENDENT_SOURCE_SLOPES_V1' in s
assert 'rawLongPct=' in s and 'fullLongPct=' in s
assert 'deltaLongPp=' in s and 'deltaCrossPp=' in s
assert 'fit!!.dHdForward' in s and 'fit!!.dHdRight' in s
assert 'independentGroundTruth=false' in s
assert 'INSUFFICIENT_DUAL_SOURCE' in s
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'precisionLastDiagnostic += " | " + depthSourceVerdict.diagnostic' in m
assert 'PrecisionDepthRecoveryAdvisor' in m
assert 'depthRecovery.offerRestart' in m
assert 'precisionConsecutiveNoDepthScans' in m
assert 'depthHealth.state,finalDepthDecision' in m
assert 'depth_restart_requested_at' in m
assert 'recreate()' in m
assert 'terminal: Boolean' in p and 'consecutiveNoDepthScans' in p
assert 'secondConsecutiveCompleteNoDepthScanOffersOptInOnly' in r
assert 'establishedVetoPolicyForCrossSlopeDoesNotChange' in t
assert 'PrecisionProjectionRayAudit.cameraRay(' in (root/"precision/PrecisionDepthCollector.kt").read_text()
assert 'PrecisionGroundPlaneBiasAudit.diagnostic(' in (root/"precision/PrecisionDepthCollector.kt").read_text()
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionDepthFreshnessPolicy.evaluate(' in (root/"precision/PrecisionDepthCollector.kt").read_text()
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m
print("v10.5: signed source slopes and user-authorized Depth restart safety invariants PASS")
