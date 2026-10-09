"""Precision v10.1: reject stale ARCore Depth timestamps and preserve acquisition provenance.

2026-10-10 M07: normal Depth-to-camera age -1..10 ms; reused Raw images
were up to 29,250 ms old while Full images remained ~6..9 ms fresh.
Reprojecting an old Depth image using a NEW camera pose is unsafe.
Do not fabricate old camera poses or compensate slope numerically.
"""
from pathlib import Path

root = Path("app/src/main/java/jp/example/greenreader")
collector = root / "precision/PrecisionDepthCollector.kt"
freshness = root / "precision/PrecisionDepthFreshnessPolicy.kt"
policy = root / "precision/PrecisionFullDepthSupplementPolicy.kt"
main = root / "MainActivity.kt"
gradle = Path("app/build.gradle.kts")
guard_test = Path("app/src/test/java/jp/example/greenreader/precision/PrecisionDepthFreshnessPolicyTest.kt")
old_test = Path("app/src/test/java/jp/example/greenreader/precision/PrecisionSparseRawFallbackTest.kt")

c=collector.read_text(encoding="utf8")
p=policy.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
t=old_test.read_text(encoding="utf8")

def one(src,old,new,tag):
    n=src.count(old)
    if n!=1: raise RuntimeError(f"v10.1 {tag}: expected 1 match; found {n}")
    return src.replace(old,new,1)

freshness.write_text("""package jp.example.greenreader.precision

/**
 * ARCore camera Frame and Depth image timestamps share the monotonic timebase.
 * Geometric backprojection in PrecisionDepthCollector uses the camera pose
 * at the current frame time. A significantly older Depth image cannot be
 * safely reconstructed using this pose.
 *
 * This policy intentionally *rejects* stale measurements rather than
 * extrapolating unobserved geometry. Age tolerance is acquisition engineering,
 * not proof of absolute green slope accuracy.
 */
object PrecisionDepthFreshnessPolicy {
    const val MAX_ABS_AGE_NS: Long = 250_000_000L

    data class Verdict(val acceptable: Boolean, val ageNs: Long)

    fun evaluate(cameraFrameTimestampNs: Long, depthImageTimestampNs: Long): Verdict {
        if (cameraFrameTimestampNs <= 0L || depthImageTimestampNs <= 0L)
            return Verdict(false, 0L)
        val ageNs = cameraFrameTimestampNs - depthImageTimestampNs
        return Verdict(ageNs in -MAX_ABS_AGE_NS..MAX_ABS_AGE_NS, ageNs)
    }
}
""",encoding="utf8")

c=one(c,"    private var duplicateFullFrames = 0\n",
"""    private var duplicateFullFrames = 0
    private var staleRawDepthFrames = 0
    private var staleFullDepthFrames = 0
    private var acquiredRawPointCount = 0L
    private var acquiredFullPointCount = 0L
""","counters")
c=one(c,"        duplicateFullFrames = 0\n",
"""        duplicateFullFrames = 0
        staleRawDepthFrames = 0
        staleFullDepthFrames = 0
        acquiredRawPointCount = 0L
        acquiredFullPointCount = 0L
""","counter reset")
c=one(c,"        val duplicateFullFrames: Int = 0,\n",
"""        val duplicateFullFrames: Int = 0,
        val staleRawDepthFrames: Int = 0,
        val staleFullDepthFrames: Int = 0,
        val acquiredRawPointCount: Long = 0L,
        val acquiredFullPointCount: Long = 0L,
""","snapshot schema")
c=one(c,"                    duplicateFullFrames = items.sumOf { it.duplicateFullFrames },\n",
"""                    duplicateFullFrames = items.sumOf { it.duplicateFullFrames },
                    staleRawDepthFrames = items.sumOf { it.staleRawDepthFrames },
                    staleFullDepthFrames = items.sumOf { it.staleFullDepthFrames },
                    acquiredRawPointCount = items.sumOf { it.acquiredRawPointCount },
                    acquiredFullPointCount = items.sumOf { it.acquiredFullPointCount },
""","snapshot aggregate")
c=one(c,"        duplicateFullFrames = duplicateFullFrames,\n",
"""        duplicateFullFrames = duplicateFullFrames,
        staleRawDepthFrames = staleRawDepthFrames,
        staleFullDepthFrames = staleFullDepthFrames,
        acquiredRawPointCount = acquiredRawPointCount,
        acquiredFullPointCount = acquiredFullPointCount,
""","snapshot construction")
c=one(c,'''        " duplicateFull=" + duplicateFullFrames +
''',
'''        " duplicateFull=" + duplicateFullFrames +
        " staleRawDepth=" + staleRawDepthFrames +
        " staleFullDepth=" + staleFullDepthFrames +
        " acquiredRawPoints=" + acquiredRawPointCount +
        " acquiredFullPoints=" + acquiredFullPointCount +
''', "diagnosticSummary")

c=one(c,"""        val timestamp = depth.timestamp
        if (isRaw) {""",
"""        val timestamp = depth.timestamp
        // Reject stale/invalid native images before pixel extraction or
        // reconstruction with the CURRENT camera pose. ARCore on M07 can
        // repeatedly return Raw images >29 seconds old while camera tracks.
        val freshness = PrecisionDepthFreshnessPolicy.evaluate(frame.timestamp, timestamp)
        if (!freshness.acceptable) {
            if (isRaw) staleRawDepthFrames++ else staleFullDepthFrames++
            return false
        }
        if (isRaw) {""","guard stale before reproject")

c=one(c,"""            if (isRaw) lastRawAcceptedPointCount = added
""",
"""            if (isRaw) {
                lastRawAcceptedPointCount = added
                acquiredRawPointCount += added.toLong()
            } else {
                acquiredFullPointCount += added.toLong()
            }
""","untruncated accepted source evidence")

p=one(p,
"""        rawFrames >= 4 && rawPoints > 0 && fullPoints >= 2200 &&
            rawPoints.toLong() < rawFrames.toLong() * MIN_RAW_POINTS_PER_FRAME &&
            !independentSourcesAgree""",
"""        // The archived point reservoir can evict almost all Raw records
        // when Full fills it. Absence of stored Raw frames is NOT positive
        // evidence of trustworthy Full-sourced directional geometry.
        fullPoints >= 2200 && !independentSourcesAgree &&
            (rawFrames < 4 || rawPoints <= 0 ||
                rawPoints.toLong() <
                    rawFrames.toLong() * MIN_RAW_POINTS_PER_FRAME ||
                fullPoints.toLong() > 2L * rawPoints.toLong())""",
"fail-closed for full-dominated scans even if raw absent")

m=one(m,
"""        val sparseMixedUnverified =
            jp.example.greenreader.precision.PrecisionFullDepthSupplementPolicy
                .suppressSparseMixedDirection(
                    rawPoints = depthSourceVerdict.raw.points,
                    rawFrames = depthSourceVerdict.raw.uniqueFrames,
                    fullPoints = depthSourceVerdict.full.points,
                    independentSourcesAgree = depthSourceVerdict.crossSourceVerified
                )""",
"""        // The saved aggregate reservoir can drop historic Raw frames when
        // Full reaches 90k points. Audit the ORIGINAL acquired source totals,
        // aggregated across scan windows, not the truncated output CSV.
        val depthAcquisitionTotals =
            jp.example.greenreader.precision.PrecisionDepthCollector
                .DiagnosticsSnapshot.aggregate(precisionCollectorWindowSnapshots)
        val sparseMixedUnverified =
            jp.example.greenreader.precision.PrecisionFullDepthSupplementPolicy
                .suppressSparseMixedDirection(
                    rawPoints = depthAcquisitionTotals.acquiredRawPointCount
                        .coerceAtMost(Int.MAX_VALUE.toLong()).toInt(),
                    rawFrames = depthAcquisitionTotals.rawAcceptedFrames,
                    fullPoints = depthAcquisitionTotals.acquiredFullPointCount
                        .coerceAtMost(Int.MAX_VALUE.toLong()).toInt(),
                    independentSourcesAgree = depthSourceVerdict.crossSourceVerified
                )""","non-truncated source count for trust gate")

m=one(m,
""" + " | SPARSE_RAW_FULL_UNVERIFIED=" + sparseMixedUnverified""",
""" + " | DEPTH_FRESHNESS staleRaw=" + depthAcquisitionTotals.staleRawDepthFrames +
            " staleFull=" + depthAcquisitionTotals.staleFullDepthFrames +
            " rawAcquiredP=" + depthAcquisitionTotals.acquiredRawPointCount +
            " fullAcquiredP=" + depthAcquisitionTotals.acquiredFullPointCount +
            " | SPARSE_RAW_FULL_UNVERIFIED=" + sparseMixedUnverified""",
"archive freshness and acquisition counts")

t=one(t,
"""        assertFalse(policy.suppressSparseMixedDirection(80, 1, 60000, false))
        assertFalse(policy.suppressSparseMixedDirection(0, 150, 60000, false))""",
"""        assertTrue(policy.suppressSparseMixedDirection(80, 1, 60000, false))
        assertTrue(policy.suppressSparseMixedDirection(0, 150, 60000, false))
        assertTrue(policy.suppressSparseMixedDirection(1573, 5, 82800, false))
        assertFalse(policy.suppressSparseMixedDirection(42000, 99, 2000, false))""",
"update mixed-source safety expectations")
guard_test.write_text("""package jp.example.greenreader.precision

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionDepthFreshnessPolicyTest {
    private fun isFresh(ageMs: Long) =
        PrecisionDepthFreshnessPolicy.evaluate(
            32_000_000_000L, 32_000_000_000L - ageMs * 1_000_000L
        ).acceptable

    @Test fun healthyM07CameraDepthOffsetsRemainValid() {
        for (age in listOf(-1L, 0L, 3L, 5L, 8L, 10L, 40L, 249L, 250L)) {
            assertTrue("age=$age ms", isFresh(age))
        }
    }
    @Test fun staleRawFramesFromRealFieldLogsRejected() {
        for (age in listOf(251L, 275L, 1345L, 2348L, 2715L, 3250L,
            3350L, 9500L, 22500L, 29250L, -251L)) {
            assertFalse("age=$age ms", isFresh(age))
        }
    }
    @Test fun invalidTimestampIsNeverGroundEvidence() {
        assertFalse(PrecisionDepthFreshnessPolicy.evaluate(0L, 100L).acceptable)
        assertFalse(PrecisionDepthFreshnessPolicy.evaluate(100L, 0L).acceptable)
        assertFalse(PrecisionDepthFreshnessPolicy.evaluate(-100L, 100L).acceptable)
    }
}
""",encoding="utf8")

if m.count("Precision 10.0") < 2:
    raise RuntimeError("v10.1 app version string missing")
m=m.replace("Precision 10.0","Precision 10.1")
g=one(g,'versionName = "10.0"','versionName = "10.1"',"versionName")
g=one(g,'versionCode = 1000','versionCode = 1010',"versionCode")
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m

collector.write_text(c,encoding="utf8")
policy.write_text(p,encoding="utf8")
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
old_test.write_text(t,encoding="utf8")
print("v10.1: reject stale Depth re-projection, aggregate full/raw evidence without reservoir loss; fail-closed Full direction")
