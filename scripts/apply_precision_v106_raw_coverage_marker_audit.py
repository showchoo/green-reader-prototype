"""v10.6 SC-52A coverage-aware Full Depth fallback + endpoint offset audit.

Acquisition improvement only: dense but spatially localized/vertically
implausible Raw pixel clusters should not prevent Full supplementation.
No changes to the original ground selector, physics, marker coordinate,
Raw/Full slope veto or quality thresholds. Marker endpoint offsets are
diagnostic-only and never automatically recalibrate either signal.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
collector=root/"precision/PrecisionDepthCollector.kt"
policy=root/"precision/PrecisionFullDepthSupplementPolicy.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
c=collector.read_text(encoding="utf8")
p=policy.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(src,old,new,tag):
    n=src.count(old)
    if n != 1:
        raise RuntimeError(f"v10.6 {tag}: expected once, found {n}")
    return src.replace(old,new,1)

# Existing tests intentionally retain previous behavior when no spatial
# evidence is supplied. Live collector supplies a real per-frame assessment.
p=one(p,
'''        rawPointsInFrame: Int = if (rawAccepted) Int.MAX_VALUE else 0
    ): Plan {''',
'''        rawPointsInFrame: Int = if (rawAccepted) Int.MAX_VALUE else 0,
        rawFloorCovered: Boolean = true
    ): Plan {''',
"new coverage parameter with backwards-compatible default")
p=one(p,
'''        if (!rawAccepted || rawPointsInFrame < MIN_RAW_POINTS_PER_FRAME) {''',
'''        // Spatial support is independent of count and confidence.
        // Dense off-ground points must not disable Full Depth supplementation.
        if (!rawAccepted || rawPointsInFrame < MIN_RAW_POINTS_PER_FRAME ||
            !rawFloorCovered) {''',
"full supplement when Raw floor span is missing")

c=one(c,
'''    private var lastRawAcceptedPointCount = 0
    private var sparseRawFrames = 0''',
'''    private var lastRawAcceptedPointCount = 0
    private var rawFloorPoorFrames = 0
    private var rawFloorSupplementFrames = 0
    private var lastRawFloorCoverageDiagnostic = "not yet evaluated"
    private var sparseRawFrames = 0''',
"coverage stats fields")
c=one(c,
'''        lastRawAcceptedPointCount = 0
        sparseRawFrames = 0''',
'''        lastRawAcceptedPointCount = 0
        rawFloorPoorFrames = 0
        rawFloorSupplementFrames = 0
        lastRawFloorCoverageDiagnostic = "not yet evaluated"
        sparseRawFrames = 0''',
"per-window counters reset")

c=one(c,
'''    private fun integrateImage(
        frame: Frame,''',
'''    private fun integrateImage(
        frame: Frame,''',
"sanity integrateImage unique")
c=one(c,
'''        maxDepthM: Float = 5f
    ) {
        val camera = frame.camera''',
'''        maxDepthM: Float = 5f,
        cupPose: Pose? = null
    ) {
        val camera = frame.camera''',
"optional tracked cup pose parameter to scan integration")

c=one(c,
'''        val rawPointsInFrame = if (rawAccepted) lastRawAcceptedPointCount else 0
        rawPointTotal += rawPointsInFrame''',
'''        val rawPointsInFrame = if (rawAccepted) lastRawAcceptedPointCount else 0
        // Uses ONLY the current accepted Raw tail, not accumulated Full points.
        // A bounded sample avoids expensive extra allocations on dense frames.
        val cupLocal = cupPose?.let {
            GravityAlignedFrame.fromPose(referencePose).worldToLocal(it.translation)
        }
        val rawTail = if (rawAccepted && rawPointsInFrame > 0) {
            samples.takeLast(rawPointsInFrame.coerceAtMost(5000))
        } else emptyList()
        val rawFloorCoverage = PrecisionRawFloorCoveragePolicy.evaluate(
            rawTail,cupLocal
        )
        lastRawFloorCoverageDiagnostic = rawFloorCoverage.diagnostic()
        if (rawAccepted && !rawFloorCoverage.valid) rawFloorPoorFrames++
        rawPointTotal += rawPointsInFrame''',
"real-world Raw corridor evidence after Raw integration")

c=one(c,
'''            rawPointsInFrame = rawPointsInFrame
        )''',
'''            rawPointsInFrame = rawPointsInFrame,
            rawFloorCovered = rawFloorCoverage.valid
        )''',
"pass corridor coverage to Full supplement decision")

c=one(c,
'''                fullAcquiredFrames++
                fallbackFrames++
                if (rawPointsInFrame in 1 until''',
'''                fullAcquiredFrames++
                fallbackFrames++
                if (rawAccepted && !rawFloorCoverage.valid)
                    rawFloorSupplementFrames++
                if (rawPointsInFrame in 1 until''',
"count actually acquired Full because of poor Raw spatial support")

c=one(c,
'''        " sparseRawFrames=" + sparseRawFrames +''',
'''        " rawFloorPoorFrames=" + rawFloorPoorFrames +
        " rawFloorFullFrames=" + rawFloorSupplementFrames +
        " sparseRawFrames=" + sparseRawFrames +''',
"collector raw-floor summary")

c=one(c,
'''            projectionRayAudit.diagnostic()''',
'''            projectionRayAudit.diagnostic() + "\\n" +
            "RAW_FLOOR_COVERAGE_TOTALS_V1 poorFrames=" + rawFloorPoorFrames +
            " fullAcquiredBecausePoor=" + rawFloorSupplementFrames + "\\n" +
            lastRawFloorCoverageDiagnostic''',
"append spatial evidence to per-window archive")

m=one(m,
'''                        maxDepthM = precisionScanMaxDepthM
                    )''',
'''                        maxDepthM = precisionScanMaxDepthM,
                        cupPose = cupAnchor
                            ?.takeIf { it.trackingState == TrackingState.TRACKING }
                            ?.pose
                    )''',
"supply active cup anchor to live Raw coverage policy")

m=one(m,
'''        precisionLastDiagnostic += " | " + markerDepthCheck.summary()''',
'''        precisionLastDiagnostic += " | " + markerDepthCheck.summary()
        // Observe EACH endpoint separately: equal common-mode marker offsets
        // can cancel in the older delta-only consistency diagnostic.
        precisionLastDiagnostic += " | " +
            jp.example.greenreader.precision.PrecisionMarkerFloorOffsetAudit
                .evaluate(aggregateSurface,marks.first,marks.second).diagnostic()''',
"persist independent marker-to-depth endpoint height offsets")

if m.count("Precision 10.5") < 2:
    raise RuntimeError("v10.6 expected v10.5 version labels")
m=m.replace("Precision 10.5","Precision 10.6")
g=one(g,'versionName = "10.5"','versionName = "10.6"',"versionName")
g=one(g,'versionCode = 1050','versionCode = 1060',"versionCode")

# No write of production slope, anchored ground selector, trust or marker pose.
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionFullDepthSupplementPolicy.plan(' in c
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'PrecisionDepthFreshnessPolicy.evaluate(' in c
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m

collector.write_text(c,encoding="utf8")
policy.write_text(p,encoding="utf8")
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v10.6: conservative Raw spatial floor coverage fallback and separate marker endpoint offsets")
