"""Precision v8.2: disallow forward-height aliasing in paired lateral verification.

A 5cm forward mismatch can become ~1-2 percentage points of spurious
cross slope on a steep green. Use paired flank positions within 1.5cm
so large longitudinal grade cannot manufacture a false cross-slope veto.
Fail inconclusive instead of guessing.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
policy=root/"precision/PrecisionPairedFlankAudit.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
a=policy.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
def one(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit(f"v8.2 {label}: expected one target, found {n}")
    return src.replace(old,new,1)

a=one(a,
'''    private const val MIN_LATERAL_SEPARATION_M = 0.24f''',
'''    private const val MIN_LATERAL_SEPARATION_M = 0.24f
    // At 12% forward grade, 5cm offset can fabricate >1pp of sideways
    // grade; 1.5cm limits this effect to <=0.75pp for >=24cm flank gap.
    private const val MAX_ALONG_SIDE_MISMATCH_M = 0.015f''',
"explicit along-distance limit")
a=one(a,
'''        val slopes = ArrayList<Float>(SLICES)
        var opposing = 0''',
'''        val slopes = ArrayList<Float>(SLICES)
        var alongMismatchedSlices = 0
        var opposing = 0''',
"track side alignment rejection")
a=one(a,
'''            if (ds > 0.05f) continue''',
'''            if (ds > MAX_ALONG_SIDE_MISMATCH_M) {
                alongMismatchedSlices++
                continue
            }''',
"tighten side alignment for steep greens")
a=one(a,
'''        val m = if (slopes.isNotEmpty()) median(slopes) else null
        if (slopes.size < MIN_VALID_SLICES) {''',
'''        val m = if (slopes.isNotEmpty()) median(slopes) else null
        if (slopes.size < MIN_VALID_SLICES) {''',
"preserve no-overclaim behavior")
# Surface-fit and downstream PuttAdvisor are unchanged.
s=one(s,"Precision 8.1","Precision 8.2","app metadata")
g=one(g,'versionName = "8.1"','versionName = "8.2"',"version name")
g=one(g,'versionCode = 810','versionCode = 820',"version code")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert 'button("次のホール")' in s and 'button("結果入力")' in s
assert "precision_depth_sources.csv" in (root/"field/ScanFieldRecorder.kt").read_text()
assert "OPPOSITE_PAIRED_HEIGHTS" in a
policy.write_text(a,encoding="utf8")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied v8.2 forward-matched cross-slope safety audit")
