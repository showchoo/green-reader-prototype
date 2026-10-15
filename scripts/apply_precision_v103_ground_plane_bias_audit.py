"""v10.3 wire diagnostic-only Raw/Full/ARCore ground plane comparison.

The two new Kotlin sources and test are checked into the repository.
Run this patch only after generating the known-good v10.2 source tree.
Never change production point selection, slope, marker or safety gates.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
collector=root/"precision/PrecisionDepthCollector.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
c=collector.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(s,old,new,tag):
    n=s.count(old)
    if n!=1: raise RuntimeError(f"v10.3 {tag}: expected 1 match, found {n}")
    return s.replace(old,new,1)

c=one(c,
'''    private val framePoseTelemetry = PrecisionFramePoseTelemetry.Buffer()''',
'''    private val framePoseTelemetry = PrecisionFramePoseTelemetry.Buffer()
    private val arFloorPlaneSampler = PrecisionARFloorPlaneSampler()''',
"AR plane collector field")
c=one(c,
'''        framePoseTelemetry.clear()
        frameTimestamps.clear()''',
'''        framePoseTelemetry.clear()
        arFloorPlaneSampler.clear()
        frameTimestamps.clear()''',
"reset plane audit between scan windows")
c=one(c,
'''    @Synchronized fun framePoseDiagnostics(): String =
        framePoseTelemetry.toDiagnosticText() + "\\n" +
            PrecisionSourceOverlapAudit.diagnostic(samples)''',
'''    @Synchronized fun framePoseDiagnostics(): String =
        framePoseTelemetry.toDiagnosticText() + "\\n" +
            PrecisionSourceOverlapAudit.diagnostic(samples) + "\\n" +
            PrecisionGroundPlaneBiasAudit.diagnostic(
                samples, arFloorPlaneSampler.snapshot()
            )''',
"persist independent per-window plane comparisons")
c=one(c,
'''        lastRequestedMaxDepthM = maxDepthM
        attemptedFrames++

        // Keep the recent tracked AR Frame poses independently''',
'''        lastRequestedMaxDepthM = maxDepthM
        attemptedFrames++
        // Observe ARCore plane updates even when a Depth image is unavailable.
        // This is strictly diagnostic: failed plane access does not block Raw.
        try {
            arFloorPlaneSampler.observe(frame, referencePose)
        } catch (_: Throwable) {
            // Preserve the exact existing scan / measurement behavior.
        }

        // Keep the recent tracked AR Frame poses independently''',
"observe current tracked frame planes")

if m.count("Precision 10.2")<2:
    raise RuntimeError("v10.3 expected v10.2 labels in generated MainActivity")
m=m.replace("Precision 10.2","Precision 10.3")
g=one(g,'versionName = "10.2"','versionName = "10.3"',"versionName")
g=one(g,'versionCode = 1020','versionCode = 1030',"versionCode")

assert (root/"precision/PrecisionGroundPlaneBiasAudit.kt").exists()
assert (root/"precision/PrecisionARFloorPlaneSampler.kt").exists()
assert Path("app/src/test/java/jp/example/greenreader/precision/PrecisionGroundPlaneBiasAuditTest.kt").exists()
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m

collector.write_text(c,encoding="utf8")
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v10.3: per-window independent Raw/Full/ARCore plane bias diagnostics")
