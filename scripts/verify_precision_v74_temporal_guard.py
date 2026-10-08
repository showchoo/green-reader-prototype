"""Ensure v7.4 temporal safety and reservoir changes survived all patch stages."""
from pathlib import Path
main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf8")
analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf8")
temporal = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionTemporalConsistency.kt").read_text(encoding="utf8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf8")

assert 'versionName = "7.4"' in gradle and 'versionCode = 740' in gradle
assert 'appVersion = "Precision 7.4"' in main
assert "precisionReservoirRandom.nextInt(precisionLogPointsSeen)" in main
assert "precisionLogPointsSeen += 1" in main
assert "precisionLogPoints.size < 90000" in main
assert main.count("precisionWindowGlobalSlopes.clear()") >= 2
assert "PrecisionSlopeAnalyzer.lastGlobalSlopePercent" in main
assert "PrecisionTemporalConsistency.evaluate(precisionWindowGlobalSlopes)" in main
assert "if (precisionTemporalUnstable) combined = null" in main
assert 'TEMPORAL' in temporal
assert 'thresholdPp: Float = 2.5f' in temporal
assert 'values.size < 4' in temporal
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in analyzer
assert "MAX_LOCAL_RMSE_METERS = 0.040" in analyzer
assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer
assert "precisionCompletedDiagnostic = precisionLastDiagnostic" in main
assert 'button("結果入力")' in main
assert 'button("次のホール")' in main
assert "ScanFieldRecorder.savePuttResult" in main
assert "bitmap = failureBitmap" in main
print("Precision v7.4 source regression checks passed")
