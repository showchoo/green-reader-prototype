"""v9.9 ground reference must come from physical ball vicinity, never scene majority."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
p=root/"precision/PrecisionSurfaceBuilder.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
s=p.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
start=s.find("        // Stage 1b: estimate the actual turf reference height from stable cells close")
end=s.find("        val initial = ArrayList<Candidate>()",start)
if start<0 or end<0:raise SystemExit("v9.9 global-height reference not found")
replacement='''        // Estimate only from repeated, local samples around ball anchor.
        // The anchor is a coarse sanity envelope, not physical ground truth.
        val anchorSelection = if (ball != null) {
            PrecisionAnchoredGroundSelector.select(
                stable.map {
                    PrecisionAnchoredGroundSelector.Observation(
                        x = (it.key.x + 0.5f) * voxelSizeMeters,
                        z = (it.key.z + 0.5f) * voxelSizeMeters,
                        height = it.med
                    )
                }, ball
            )
        } else null
        // Preserve legacy generic surface builder when no marker was provided.
        // Precision scans always pass an actual ball/cup, so the strict
        // anchored selector cannot fall back to the global height histogram.
        val unanchoredHeights = if (ball == null) {
            val bins = stable.groupBy { floor(it.med / .05f).toInt() }
            val winner = bins.maxByOrNull { it.value.size }?.key
            if (winner == null) emptyList() else stable.mapNotNull {
                if (abs(it.med - (winner + .5f) * .05f) <= .10f) it.med else null
            }.sorted()
        } else emptyList()
        val groundReference = if (ball == null) median(unanchoredHeights)
            else anchorSelection?.referenceHeight ?: Float.NaN

'''
s=s[:start]+replacement+s[end:]
old='''                val radius = hypot(x.toDouble(), z.toDouble()).toFloat()'''
new='''                val radius = if (ball != null) {
                    hypot((x - ball.x).toDouble(), (z - ball.z).toDouble()).toFloat()
                } else hypot(x.toDouble(), z.toDouble()).toFloat()'''
if s.count(old)!=1:raise SystemExit("v9.9 radial height band missing")
s=s.replace(old,new,1)
if s.count('dominantHeights.size')!=1:raise SystemExit("v9.9 diagnostic reference count missing")
s=s.replace('dominantHeights.size', '(if (ball == null) unanchoredHeights.size else anchorSelection?.matchedHeightCount ?: 0)')
if s.count(' + marksText + rawSpanText')!=1:raise SystemExit("v9.9 stage diagnostic missing")
s=s.replace(' + marksText + rawSpanText',' + " " + (anchorSelection?.diagnostic() ?: "ANCHORED_GROUND status=NO_BALL_ANCHOR") + marksText + rawSpanText')
start=s.find("        val seedKeys = initial\n")
end=s.find("        // If no ground can be established near the ball",start)
if start<0 or end<0:raise SystemExit("v9.9 global seed selection not found")
s=s[:start]+'''        // Precision scans seed strictly from the marked ball vicinity.
        // Unanchored API callers (legacy generic tests) retain the original
        // region selection; they are NOT used by the precision scan flow.
        val seedKeys = if (ball == null) {
            initial.filter { abs(it.cell.height - groundReference) <= .14f }
                .sortedWith(compareBy<Candidate> {
                    hypot(it.cell.x.toDouble(), it.cell.z.toDouble())
                }.thenBy { abs(it.cell.height - groundReference) })
                .take(16).map { it.key }
        } else if (anchorSelection?.valid == true) {
            anchorSelection.seedIndices.mapNotNull { i ->
                val k = stable[i].key
                if (map.containsKey(k)) k else null
            }.distinct().take(16)
        } else emptyList()

'''+s[end:]
assert 'PrecisionAnchoredGroundSelector.select(' in s
assert 'ANCHORED_GROUND status=' in s
assert "heightBins" not in s and "dominantBin" not in s
p.write_text(s,encoding="utf8")
if m.count("Precision 9.8")<2:raise SystemExit("missing v9.8 app labels")
m=m.replace("Precision 9.8","Precision 9.9")
if g.count('versionName = "9.8"')!=1 or g.count('versionCode = 980')!=1:
    raise SystemExit("v9.9 Gradle base not v9.8")
g=g.replace('versionName = "9.8"','versionName = "9.9"')
g=g.replace('versionCode = 980','versionCode = 990')
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v9.9: anchor-supported near-ball reference and connected floor selection")
