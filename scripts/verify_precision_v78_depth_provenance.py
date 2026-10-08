"""v7.8 source-provenance sidecar guards; preserve historical depth CSV."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
models=(root/"precision/PrecisionModels.kt").read_text(encoding="utf8")
collector=(root/"precision/PrecisionDepthCollector.kt").read_text(encoding="utf8")
rec=(root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
main=(root/"MainActivity.kt").read_text(encoding="utf8")
gradle=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "7.8"' in gradle and 'versionCode = 780' in gradle
assert 'appVersion = "Precision 7.8"' in main
assert 'val depthSource: String = "unknown"' in models
assert 'confs[i], timestamp, "raw")' in collector
assert 'confs[i], timestamp, "full")' in collector
assert rec.count('precision_depth_sources.csv') == 2
assert 'writePrecisionSources(out, precisionPoints)' in rec
assert 'index,frame_timestamp_ns,depth_source' in rec
assert 'index,x_m,y_m,z_m,confidence,frame_timestamp_ns' in rec
assert 'button("カップ再指定")' in main
assert 'markerGeometryTrusted = precisionMarkerGeometry()?.needsReview != true' in main
assert 'Depth Raw=' in main
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert 'bitmap = failureBitmap' in main
print("Precision v7.8 depth source provenance regression checks passed")
