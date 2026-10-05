"""Regression guard for Green Reader Precision v7.1 user/developer UI split."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")

assert 'versionName = "7.1"' in gradle
assert 'versionCode = 710' in gradle
assert 'appVersion = "Precision 7.1"' in main

# User-facing quality stays useful but does not expose internal algorithm labels.
assert '"測定信頼度 "' in main
assert '"推定誤差 ±"' in main
assert '"高精度"' in main
assert '"標準"' in main
assert '"再測定推奨"' in main
assert '"Putt "' in main and '"Scan "' in main

# Developer telemetry remains available for field testing.
assert '"開発者診断"' in main
assert "copyLastPrecisionDiagnostic()" in main
assert "precisionLastDiagnostic" in main
assert "PrecisionQualityEstimator.evaluate(" in main
assert "precisionTrackingMonitor.observe(" in main
assert "precisionCollectorWindowSnapshots" in main
assert "ScanFieldRecorder.saveGrouped(" in main
assert "ScanFieldRecorder.saveFailureGrouped(" in main

# Measurement gates stay unchanged.
analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf-8")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in analyzer
assert "MAX_LOCAL_RMSE_METERS = 0.040" in analyzer
assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer

print("Precision v7.1 user/developer UI regression checks passed")
