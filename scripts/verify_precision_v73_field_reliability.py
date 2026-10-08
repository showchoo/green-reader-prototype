"""Regression guards for M07 field data corrections in Green Reader Precision v7.3."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")
rec = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt").read_text(encoding="utf-8")
quality = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionQualityEstimator.kt").read_text(encoding="utf-8")
analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf-8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")

assert 'versionName = "7.3"' in gradle and "versionCode = 730" in gradle
assert 'appVersion = "Precision 7.3"' in main

for fun in ("metadataJson", "failureMetadataJson"):
    section = rec[rec.index("private fun " + fun + "("):]
    raw_start = section.index('return """{') + len('return """')
    raw_end = section.index('"""', raw_start)
    template = section[raw_start:raw_end]
    assert '"schema_version"' in template
    assert r'\"schema_version\"' not in template
    assert r'\"viewport\"' not in template

assert main.count("precisionFieldCollectorSummary()") >= 3
assert "DiagnosticsSnapshot.aggregate(snapshots)" in main
assert "precisionCompletedDiagnostic = precisionLastDiagnostic" in main
assert main.count("precisionCompletedDiagnostic.ifBlank") >= 2
assert '" analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"' in main

assert "precisionLastScanFailed = true" in main
assert "測定不成立" in main
assert "report == null -> TIER_LOW_CONFIDENCE" in quality
assert "score >= 85 && windowReports.size >= 2" in quality
assert "推定ばらつき" in main

assert '            } else "null") +' in analyzer
assert '" valid=" + segments.size' in analyzer
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in analyzer
assert "MAX_LOCAL_RMSE_METERS = 0.040" in analyzer
assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer

assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert "ScanFieldRecorder.savePuttResult" in main
assert "bitmap = failureBitmap" in main
assert "putt_result_$stamp.json" in rec

print("Precision v7.3 M07 field reliability checks passed")
