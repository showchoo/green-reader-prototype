"""Regression checks for v7.6 marker trust and preserved field features."""
from pathlib import Path
root = Path("app/src/main/java/jp/example/greenreader")
main = (root/"MainActivity.kt").read_text(encoding="utf8")
gate = (root/"precision/PrecisionMarkerCandidateGate.kt").read_text(encoding="utf8")
geom = (root/"precision/PrecisionMarkerGeometry.kt").read_text(encoding="utf8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "7.6"' in gradle and 'versionCode = 760' in gradle
assert 'appVersion = "Precision 7.6"' in main
assert 'PrecisionMarkerGeometry.maxVerticalDifference(horizontal)' in gate
assert 'PrecisionMarkerGeometry.maxVerticalDifference(horizontal)' in main
assert 'button("ボール再指定")' in main
assert 'button("カップ再指定")' in main
assert 'button("実測距離")' in main
assert 'precisionReferenceDistanceMeters = null' in main
assert 'precisionMarkGeometryText()' in main
assert 'MARK_GEOMETRY' in main
assert 'referenceWarning' in geom
assert 'horizontalMeters * 0.12f + 0.01f' in geom
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert "precisionCompletedDiagnostic = precisionLastDiagnostic" in main
assert "PrecisionTemporalConsistency.evaluate(precisionWindowGlobalSlopes)" in main
assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert 'bitmap = failureBitmap' in main
assert 'precisionCollectorWindowSnapshots' in main
assert 'ScanFieldRecorder.savePuttResult' in main
print("Precision v7.6 marker-trust regression checks passed")
