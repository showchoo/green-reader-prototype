"""Version 8.2 matched-flank safety regression guards."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
m=(root/"MainActivity.kt").read_text(encoding="utf8")
a=(root/"precision/PrecisionPairedFlankAudit.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
assert 'versionName = "8.2"' in g and 'versionCode = 820' in g
assert 'appVersion = "Precision 8.2"' in m
assert 'MAX_ALONG_SIDE_MISMATCH_M = 0.015f' in a
assert 'ds > MAX_ALONG_SIDE_MISMATCH_M' in a
assert 'alongMismatchedSlices++' in a
assert 'forwardMismatchSlices' in a
assert 'OPPOSITE_PAIRED_HEIGHTS' in a
assert 'PAIRED_HEIGHTS_AGREE' in a
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionPairedFlankAudit.evaluate(' in m
assert 'if (flankVerdict.blocksDirection ||' in m
assert 'MAX_USABLE_SLOPE_PERCENT = 12f' in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のホール")' in m
assert 'button("結果入力")' in m
assert 'button("カップ再指定")' in m
print("Precision v8.2 paired-flank distance-alignment checks passed")
