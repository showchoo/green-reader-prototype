"""v8.1 independent flank check and prior field regressions."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=(root/"MainActivity.kt").read_text(encoding="utf8")
audit=(root/"precision/PrecisionPairedFlankAudit.kt").read_text(encoding="utf8")
rec=(root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
gradle=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "8.1"' in gradle and 'versionCode = 810' in gradle
assert 'appVersion = "Precision 8.1"' in main
assert "PrecisionPairedFlankAudit.evaluate(" in main
assert 'if (flankVerdict.blocksDirection ||' in main
assert 'precisionMarkerGeometry()?.needsReview == true' in main
assert '" | " + flankVerdict.diagnostic' in main
assert "!flankVerdict.blocksDirection" in main
assert "OPPOSITE_PAIRED_HEIGHTS" in audit
assert "PAIRED_HEIGHTS_AGREE" in audit
assert "MIXED_OR_WEAK_PAIRED_HEIGHTS" in audit
assert "ds > 0.05f" in audit
assert "PrecisionDepthSourceAudit.analyze(" in main
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert "precision_depth_sources.csv" in rec
assert 'button("次のホール")' in main
assert 'button("結果入力")' in main
assert 'button("カップ再指定")' in main
assert 'bitmap = failureBitmap' in main
print("Precision v8.1 paired-flank regression checks passed")
