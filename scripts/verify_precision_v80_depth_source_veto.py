"""v8.0 protects direction against opposite Raw/Full cross-slope fits."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=(root/"MainActivity.kt").read_text(encoding="utf8")
policy=(root/"precision/PrecisionDepthSourceAudit.kt").read_text(encoding="utf8")
rec=(root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
gradle=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "8.0"' in gradle and 'versionCode = 800' in gradle
assert 'appVersion = "Precision 8.0"' in main
assert "PrecisionDepthSourceAudit.analyze(" in main
assert "if (depthSourceVerdict.blocksDirection) precisionDirectionTrustworthy = false" in main
assert '" | " + depthSourceVerdict.diagnostic' in main
assert "!depthSourceVerdict.blocksDirection" in main
assert "SOURCE_FIT_UNRESOLVED" in policy
assert "OPPOSITE_RAW_FULL" in policy
assert "RAW_FULL_MAGNITUDE_DISAGREEMENT" in policy
assert "INSUFFICIENT_DUAL_SOURCE" in policy
assert "MAX_POINTS_PER_SOURCE = 25000" in policy
assert "PrecisionSurfaceBuilder.build(sampled, ball, cup)" in policy
assert "PrecisionLocalQuadraticFitter.fit(" in policy
assert "precision_depth_sources.csv" in rec
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert "allowDirection = precisionDirectionTrustworthy" in main
assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert 'button("カップ再指定")' in main
assert 'bitmap = failureBitmap' in main
print("Precision v8.0 Raw/Full disagreement guard checks passed")
