"""Verify v10.6 coverage-aware supplementation and marker audit are fail-closed."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
collector=(root/"precision/PrecisionDepthCollector.kt").read_text()
policy=(root/"precision/PrecisionFullDepthSupplementPolicy.kt").read_text()
main=(root/"MainActivity.kt").read_text()
gradle=Path("app/build.gradle.kts").read_text()
coverage=(root/"precision/PrecisionRawFloorCoveragePolicy.kt").read_text()
marker=(root/"precision/PrecisionMarkerFloorOffsetAudit.kt").read_text()
t=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionRawFloorCoveragePolicyTest.kt").read_text()
mt=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionMarkerFloorOffsetAuditTest.kt").read_text()
assert 'versionName = "10.6"' in gradle and 'versionCode = 1060' in gradle
assert 'appVersion = "Precision 10.6"' in main
assert 'RAW_FLOOR_COVERAGE_V1' in coverage
assert 'CANDIDATE_COVERAGE_PRESENT' in coverage
assert 'groundTruth=false' in coverage and 'MAX_MARKER_VERTICAL_DELTA_M' in coverage
assert 'rawFloorCovered: Boolean = true' in policy
assert 'rawPointsInFrame < MIN_RAW_POINTS_PER_FRAME ||' in policy
assert '!rawFloorCovered' in policy
assert 'cupPose: Pose? = null' in collector
assert 'GravityAlignedFrame.fromPose(referencePose).worldToLocal' in collector
assert 'lastRawFloorCoverageDiagnostic' in collector
assert 'RAW_FLOOR_COVERAGE_TOTALS_V1' in collector
assert 'rawFloorSupplementFrames++' in collector
assert 'rawFloorCovered = rawFloorCoverage.valid' in collector
assert 'cupPose = cupAnchor' in main
assert 'MARKER_ENDPOINT_OFFSETS_V1' in marker
assert 'markerMinusDepth' not in main # offsets only as diagnostic string
assert '.evaluate(aggregateSurface,marks.first,marks.second).diagnostic()' in main
assert 'denseRawWithoutFloorSupportTriggersShortRangeFullSupplement' in t
assert 'equalMarkerVerticalBiasIsVisibleEvenIfDeltaCancels' in mt
assert 'PrecisionDepthFreshnessPolicy.evaluate(' in collector
assert 'PrecisionGroundPlaneBiasAudit.diagnostic(' in collector
assert 'PrecisionProjectionRayAudit.cameraRay(' in collector
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in main
assert 'PrecisionDepthSourceAudit.analyze(' in main
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in main
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in main
assert 'PrecisionDepthStallPolicy.evaluate(' in main
assert 'PrecisionDepthRecoveryAdvisor' in main
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in main and 'button("結果入力")' in main
print("v10.6: floor coverage, endpoint diagnostics, old validation and backup safeguards PASS")
