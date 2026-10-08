"""Regression guard for conservative v7.5 temporal confidence labeling."""
from pathlib import Path
root = Path("app/src/main/java/jp/example/greenreader")
main = (root/"MainActivity.kt").read_text(encoding="utf8")
q = (root/"precision/PrecisionQualityEstimator.kt").read_text(encoding="utf8")
policy = (root/"precision/PrecisionTemporalQualityGate.kt").read_text(encoding="utf8")
a = (root/"precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf8")
g = Path("app/build.gradle.kts").read_text(encoding="utf8")
rec = (root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
assert 'versionName = "7.5"' in g and 'versionCode = 750' in g
assert 'appVersion = "Precision 7.5"' in main
assert 'temporalCheckVerified = temporalResult.verified && !temporalResult.unstable' in main
assert 'temporalCheckVerified && score >= 85' in q
assert "PrecisionTemporalQualityGate.score(rawScore, temporalCheckVerified)" in q
assert "coerceAtMost(84)" in policy
assert "report == null -> TIER_LOW_CONFIDENCE" in q
assert 'val guidance = ((if (!temporalCheckVerified && report != null)' in q
assert 'MAX_USABLE_SLOPE_PERCENT = 12f' in a
assert 'MAX_LOCAL_RMSE_METERS = 0.040' in a
assert 'LOCAL_FIT_RADIUS_METERS = 0.32f' in a
assert 'precisionLogPoints.size < 90000' in main
assert 'PrecisionTemporalConsistency.evaluate(precisionWindowGlobalSlopes)' in main
assert 'button("結果入力")' in main
assert 'button("次のホール")' in main
assert 'bitmap = failureBitmap' in main
assert "precisionCompletedDiagnostic = precisionLastDiagnostic" in main
assert "putt_result_$stamp.json" in rec
print("Precision v7.5 quality calibration regression checks passed")
