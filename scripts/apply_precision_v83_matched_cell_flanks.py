"""v8.3: pair individual turf cells at matched forward positions.

v8.2 compared medians of entire left/right flank groups. Unequal lateral
coverage could shift one group's median forward coordinate despite several
valid same-forward pairs. Here every height comparison is between two
distinct cells at most 1.5cm apart forward; unpaired cells cannot influence
the height difference. Inconclusive remains non-vetoing.
"""
from pathlib import Path

root = Path("app/src/main/java/jp/example/greenreader")
main = root / "MainActivity.kt"
policy = root / "precision/PrecisionPairedFlankAudit.kt"
gradle = Path("app/build.gradle.kts")
a = policy.read_text(encoding="utf8")
s = main.read_text(encoding="utf8")
g = gradle.read_text(encoding="utf8")

def one(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"v8.3 {label}: expected one target; found {n}")
    return src.replace(old, new, 1)

start = "        val slopes = ArrayList<Float>(SLICES)\n"
end = "        val m = if (slopes.isNotEmpty()) median(slopes) else null\n"
if a.count(start) != 1 or a.count(end) != 1:
    raise SystemExit("v8.3 expected unique v8.2 flank loop")
i = a.index(start)
j = a.index(end, i)
if "val ds = abs(median(l.map { it.along }) -" not in a[i:j]:
    raise SystemExit("v8.3 requires original v8.2 median-based forward check")
a = a[:i] + """        val slopes = ArrayList<Float>(SLICES)
        var alongMismatchedSlices = 0
        var pairedCells = 0
        var opposing = 0
        var agreeing = 0
        for (i in 0 until SLICES) {
            val l = left[i]
            val r = right[i]
            if (l.size < MIN_CELLS_PER_SIDE || r.size < MIN_CELLS_PER_SIDE) continue

            // Greedy sorted 1:1 matching finds distinct forward-aligned
            // cell pairs in O(n log n) time; never reuse a cell or align
            // whole-side height medians taken from different positions.
            // This is a comparison, not a correction or sign inversion.
            val orderedLeft = l.sortedBy { it.along }
            val orderedRight = r.sortedBy { it.along }
            var li = 0
            var ri = 0
            val matchedSlopes = ArrayList<Float>(minOf(l.size, r.size))
            while (li < orderedLeft.size && ri < orderedRight.size) {
                val ls = orderedLeft[li]
                val rs = orderedRight[ri]
                val deltaForward = ls.along - rs.along
                when {
                    deltaForward < -MAX_ALONG_SIDE_MISMATCH_M -> li++
                    deltaForward > MAX_ALONG_SIDE_MISMATCH_M -> ri++
                    else -> {
                        val lateralGap = rs.lateral - ls.lateral
                        if (lateralGap.isFinite() &&
                            lateralGap >= MIN_LATERAL_SEPARATION_M) {
                            val pairSlope = (rs.height - ls.height) / lateralGap * 100f
                            if (pairSlope.isFinite()) matchedSlopes.add(pairSlope)
                        }
                        li++
                        ri++
                    }
                }
            }

            // A single coincident pair is not evidence of a whole-slice
            // slope. Require four independent matched cells per slice.
            if (matchedSlopes.size < MIN_CELLS_PER_SIDE) {
                alongMismatchedSlices++
                continue
            }
            pairedCells += matchedSlopes.size
            val slope = median(matchedSlopes)
            slopes.add(slope)
            if (abs(slope) >= SIGNIFICANT_CROSS_PP) {
                if (slope * reportedCrossPercent < 0f) opposing++
                else agreeing++
            }
        }
""" + a[j:]

a = one(a,
"""        val medianPairedCrossPercent: Float?,
        val forwardMismatchSlices: Int = 0
""",
"""        val medianPairedCrossPercent: Float?,
        val forwardMismatchSlices: Int = 0,
        val matchedCellPairs: Int = 0
""", "pair count field")
a = one(a,
'                " forwardMismatch=" + forwardMismatchSlices +\n',
'                " forwardMismatch=" + forwardMismatchSlices +\n'
'                " matchedPairs=" + matchedCellPairs +\n',
"pair count diagnostics")
if a.count("                opposing, m, alongMismatchedSlices)") != 2:
    raise SystemExit("v8.3 expected two paired-coverage verdict returns")
a = a.replace(
    "                opposing, m, alongMismatchedSlices)",
    "                opposing, m, alongMismatchedSlices, pairedCells)"
)
a = one(a,
"""            false, verified, slopes.size, opposing, m, alongMismatchedSlices
""",
"""            false, verified, slopes.size, opposing, m, alongMismatchedSlices, pairedCells
""", "agreement count")

s = one(s, 'appVersion = "Precision 8.2"', 'appVersion = "Precision 8.3"', "app version")
g = one(g, 'versionName = "8.2"', 'versionName = "8.3"', "gradle name")
g = one(g, 'versionCode = 820', 'versionCode = 830', "gradle code")
assert "MAX_ALONG_SIDE_MISMATCH_M = 0.015f" in a
assert 'precision_depth_sources.csv' in (root / "field/ScanFieldRecorder.kt").read_text()
assert 'button("結果入力")' in s and 'button("次のホール")' in s
assert 'PrecisionDepthSourceAudit.analyze(' in s
policy.write_text(a, encoding="utf8")
main.write_text(s, encoding="utf8")
gradle.write_text(g, encoding="utf8")
print("Applied v8.3 distinct forward-matched flank cell audit")
