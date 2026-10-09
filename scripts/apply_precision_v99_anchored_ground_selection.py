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
        val groundReference = anchorSelection?.referenceHeight ?: Float.NaN

'''
s=s[:start]+replacement+s[end:]
old='''                val radius = hypot(x.toDouble(), z.toDouble()).toFloat()'''
new='''                val radius = if (ball != null) {
                    hypot((x - ball.x).toDouble(), (z - ball.z).toDouble()).toFloat()
                } else hypot(x.toDouble(), z.toDouble()).toFloat()'''
if s.count(old)!=1:raise SystemExit("v9.9 radial height band missing")
s=s.replace(old,new,1)
if s.count('dominantHeights.size')!=1:raise SystemExit("v9.9 diagnostic reference count missing")
s=s.replace('dominantHeights.size','anchorSelection?.matchedHeightCount ?: 0')
if s.count(' + marksText + rawSpanText')!=1:raise SystemExit("v9.9 stage diagnostic missing")
s=s.replace(' + marksText + rawSpanText',' + " " + (anchorSelection?.diagnostic() ?: "ANCHORED_GROUND status=NO_BALL_ANCHOR") + marksText + rawSpanText')
start=s.find("        val seedKeys = initial\n")
end=s.find("        // If no ground can be established near the ball",start)
if start<0 or end<0:raise SystemExit("v9.9 global seed selection not found")
s=s[:start]+'''        // Use ONLY anchor-supported near-ball seeds, not scene-wide cells.
        val seedKeys = if (anchorSelection?.valid == true) {
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
