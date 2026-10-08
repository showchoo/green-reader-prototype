"""v8.4 source-level and preservation checks after the cumulative build."""
from pathlib import Path

root = Path("app/src/main/java/jp/example/greenreader")
main = (root / "MainActivity.kt").read_text(encoding="utf8")
audit = (root / "precision/PrecisionPairedFlankAudit.kt").read_text(encoding="utf8")
recorder = (root / "field/ScanFieldRecorder.kt").read_text(encoding="utf8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "8.4"' in gradle and 'versionCode = 840' in gradle
assert 'appVersion = "Precision 8.3"' in main
assert 'MAX_ALONG_SIDE_MISMATCH_M = 0.015f' in audit
assert 'val orderedLeft = l.sortedBy { it.along }' in audit
assert 'val orderedRight = r.sortedBy { it.along }' in audit
assert 'val deltaForward = ls.along - rs.along' in audit
assert 'if (matchedSlopes.size < MIN_CELLS_PER_SIDE)' in audit
assert 'li++' in audit and 'ri++' in audit
assert 'matchedPairs=' in audit and 'matchedCellPairs' in audit
assert 'OPPOSITE_PAIRED_HEIGHTS' in audit and 'PAIRED_HEIGHTS_AGREE' in audit
assert 'PrecisionDepthSourceAudit.analyze(' in main
assert 'PrecisionScaleDirectionAudit.evaluate(' in main
assert 'localFitRadiusMeters = 0.50f' in (root / "precision/PrecisionScaleDirectionAudit.kt").read_text(encoding="utf8")
assert 'PrecisionPairedFlankAudit.evaluate(' in main
assert 'if (flankVerdict.blocksDirection ||' in main
assert 'precisionMarkerGeometry()?.needsReview == true' in main
assert 'MAX_USABLE_SLOPE_PERCENT = 12f' in (
    root / "precision/PrecisionSlopeAnalyzer.kt"
).read_text(encoding="utf8")
assert 'precision_depth_sources.csv' in recorder
assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert 'button("カップ再指定")' in main
print("Precision v8.4 source and field-feature preservation checks passed")
