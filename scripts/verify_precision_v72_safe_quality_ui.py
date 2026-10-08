"""Regression guard for Green Reader Precision v7.2."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")
recorder = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt").read_text(encoding="utf-8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")

assert 'versionName = "7.2"' in gradle and 'versionCode = 720' in gradle
assert 'appVersion = "Precision 7.2"' in main

# v7.1 field-test features must survive unchanged.
assert "precisionHoleNumber = 1" in main
assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert "showPrecisionPuttResultDialog()" in main
assert "ScanFieldRecorder.savePuttResult" in main
assert "bitmap = failureBitmap" in main
assert '"hole_number": ${identity.holeNumber}' in recorder
assert "putt_result_$stamp.json" in recorder

# Normal UI exposes useful confidence without implementation details.
assert '"測定信頼度 "' in main
assert "推定誤差 ±" in main
assert '"高精度"' in main
assert '"標準"' in main
assert '"再測定推奨"' in main
assert '"開発者診断"' in main

# Full technical diagnostics remain available for testing/logging.
assert "precisionLastDiagnostic" in main
assert "copyLastPrecisionDiagnostic()" in main
assert "PrecisionQualityEstimator.evaluate(" in main
assert "precisionTrackingMonitor.observe(" in main
assert "precisionCollectorWindowSnapshots" in main
assert "ScanFieldRecorder.saveGrouped(" in main
assert "ScanFieldRecorder.saveFailureGrouped(" in main

# Accuracy boundaries stay unchanged.
analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf-8")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in analyzer
assert "MAX_LOCAL_RMSE_METERS = 0.040" in analyzer
assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer

print("Precision v7.2 regression checks passed")
