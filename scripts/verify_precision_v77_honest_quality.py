"""v7.7 data-quality wording and marker trust source checks."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
m=(root/"MainActivity.kt").read_text(encoding="utf8")
q=(root/"precision/PrecisionQualityEstimator.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "7.7"' in g and 'versionCode = 770' in g
assert 'appVersion = "Precision 7.7"' in m
assert "markerGeometryTrusted: Boolean = true" in q
assert "temporalCheckVerified && markerGeometryTrusted" in q
assert "markerGeometryTrusted = precisionMarkerGeometry()?.needsReview != true" in m
assert '-> "再現性良好"' in m
assert "取得データ品質" in m
assert "絶対精度は未検証" in m
assert "Depth Raw=" in m
assert 'button("カップ再指定")' in m
assert 'button("実測距離")' in m
assert 'MARK_GEOMETRY' in m
assert 'button("結果入力")' in m
assert 'button("次のホール")' in m
assert "precisionCompletedDiagnostic = precisionLastDiagnostic" in m
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
print("Precision v7.7 honest-quality regression checks passed")
