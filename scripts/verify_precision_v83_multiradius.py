"""v8.3 spatial-scale sign gate and baseline regression guards."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
m=(root/"MainActivity.kt").read_text(encoding="utf8")
a=(root/"precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf8")
s=(root/"precision/PrecisionScaleDirectionAudit.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "8.3"' in g and 'versionCode = 830' in g
assert 'appVersion = "Precision 8.3"' in m
assert 'localFitRadiusMeters: Float = LOCAL_FIT_RADIUS_METERS' in a
assert 'radiusMeters = localFitRadiusMeters' in a
assert "PrecisionScaleDirectionAudit.evaluate(" in m
assert "if (scaleVerdict.blocksDirection) precisionDirectionTrustworthy = false" in m
assert "!scaleVerdict.blocksDirection" in m
assert '" | " + scaleVerdict.diagnostic' in m
assert 'localFitRadiusMeters = 0.50f' in s
assert 'localFitRadiusMeters = 0.80f' in s
assert 'RADIUS50_OPPOSITE' in s
assert 'RADIUS80_OPPOSITE' in s
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in a
assert "PrecisionPairedFlankAudit.evaluate(" in m
assert 'MAX_ALONG_SIDE_MISMATCH_M = 0.015f' in (root/"precision/PrecisionPairedFlankAudit.kt").read_text()
assert "PrecisionDepthSourceAudit.analyze(" in m
assert "precision_depth_sources.csv" in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のホール")' in m and 'button("結果入力")' in m
assert 'button("カップ再指定")' in m
assert 'bitmap = failureBitmap' in m
print("Precision v8.3 multiscale sign safeguards passed")
