"""Precision v10.0: observed sparse Raw frames must not suppress Full Depth acquisition.

Field evidence, M07 2026-10-10:
  v9.8 healthy Raw frames: ~384-453 accepted points/frame
  v9.9 sparse Raw frames: ~8-103 accepted points/frame
The legacy boolean rawAccepted meant one usable pixel was enough to disable
Full Depth for a short putt. Acquire *additional* Full Depth evidence when
Raw is sparse; never weaken ground selection, fit, or quality thresholds.
Do not silently certify Full: sparse-Raw/Full-dominated directional guidance
remains unverified when the independent source audit lacks agreement.
"""
from pathlib import Path

root = Path("app/src/main/java/jp/example/greenreader")
policy = root / "precision/PrecisionFullDepthSupplementPolicy.kt"
collector = root / "precision/PrecisionDepthCollector.kt"
main = root / "MainActivity.kt"
gradle = Path("app/build.gradle.kts")
test = Path("app/src/test/java/jp/example/greenreader/precision/PrecisionSparseRawFallbackTest.kt")

p = policy.read_text(encoding="utf8")
c = collector.read_text(encoding="utf8")
m = main.read_text(encoding="utf8")
g = gradle.read_text(encoding="utf8")

def one(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"v10.0 {label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)

p = one(p, "object PrecisionFullDepthSupplementPolicy {\n",
"""object PrecisionFullDepthSupplementPolicy {
    // A per-frame *acquisition* threshold, NOT a ground/accuracy threshold.
    // M07 normal Raw ~400/frame; field-starved Raw ~8..103/frame.
    const val MIN_RAW_POINTS_PER_FRAME = 160

    /**
     * Sparse Raw alone cannot validate a green. If Full must fill in for it,
     * directional guidance is withheld until independent source evidence agrees.
     * This flag is distinct from scan success and absolute accuracy.
     */
    fun suppressSparseMixedDirection(
        rawPoints: Int,
        rawFrames: Int,
        fullPoints: Int,
        independentSourcesAgree: Boolean
    ): Boolean =
        rawFrames >= 4 && rawPoints > 0 && fullPoints >= 2200 &&
            rawPoints.toLong() < rawFrames.toLong() * MIN_RAW_POINTS_PER_FRAME &&
            !independentSourcesAgree

""", "policy constant and source guard")
p = one(p,
"""        ballAxialDepthM: Float
    ): Plan {
        if (!rawAccepted) return Plan(true, requestedMinDepthM)
""",
"""        ballAxialDepthM: Float,
        rawPointsInFrame: Int = if (rawAccepted) Int.MAX_VALUE else 0
    ): Plan {
        // Raw may return an image with only 8-103 usable pixels on M07.
        // A single valid Raw pixel must NOT disable Full Depth supplementation.
        if (!rawAccepted || rawPointsInFrame < MIN_RAW_POINTS_PER_FRAME) {
            return Plan(true, requestedMinDepthM)
        }
""", "sparse image fallback decision")

c = one(c, "    private var duplicateRawFrames = 0\n",
"""    private var duplicateRawFrames = 0
    private var lastRawAcceptedPointCount = 0
    private var sparseRawFrames = 0
    private var sparseRawFullAcquiredFrames = 0
    private var rawPointTotal = 0L
""", "acquisition counters")
c = one(c, "        duplicateRawFrames = 0\n",
"""        duplicateRawFrames = 0
        lastRawAcceptedPointCount = 0
        sparseRawFrames = 0
        sparseRawFullAcquiredFrames = 0
        rawPointTotal = 0L
""", "counter reset")
c = one(c, '        " duplicateRaw=" + duplicateRawFrames +\n',
"""        " sparseRawFrames=" + sparseRawFrames +
        " sparseRawFullAcquired=" + sparseRawFullAcquiredFrames +
        " rawAcceptedPointTotal=" + rawPointTotal +
        " lastRawPoints=" + lastRawAcceptedPointCount +
        " duplicateRaw=" + duplicateRawFrames +
""", "source density diagnostics")
c = one(c, "        var rawAccepted = false\n",
"""        var rawAccepted = false
        lastRawAcceptedPointCount = 0
""", "per-frame count reset")
c = one(c, "        val ballInCamera = try {\n",
"""        val rawPointsInFrame = if (rawAccepted) lastRawAcceptedPointCount else 0
        rawPointTotal += rawPointsInFrame
        if (rawPointsInFrame in 1 until
            PrecisionFullDepthSupplementPolicy.MIN_RAW_POINTS_PER_FRAME) {
            sparseRawFrames++
        }

        val ballInCamera = try {
""", "raw density threshold bookkeeping")
c = one(c, """            ballAxialDepthM = ballAxialDepthM
        )""",
"""            ballAxialDepthM = ballAxialDepthM,
            rawPointsInFrame = rawPointsInFrame
        )""", "pass real count to full policy")
c = one(c, """                fullAcquiredFrames++
                fallbackFrames++
""",
"""                fullAcquiredFrames++
                fallbackFrames++
                if (rawPointsInFrame in 1 until
                    PrecisionFullDepthSupplementPolicy.MIN_RAW_POINTS_PER_FRAME) {
                    sparseRawFullAcquiredFrames++
                }
""", "record actual sparse raw supplement")
c = one(c, "        val timestamp = depth.timestamp\n",
"""        if (isRaw) lastRawAcceptedPointCount = 0
        val timestamp = depth.timestamp
""", "invalidate count on duplicates")
c = one(c, "        if (added > 0) {\n            frameTimestamps += timestamp\n",
"""        if (added > 0) {
            if (isRaw) lastRawAcceptedPointCount = added
            frameTimestamps += timestamp
""", "record actual Raw points")

m = one(m,
"""        if (depthSourceVerdict.blocksDirection) precisionDirectionTrustworthy = false

        consensusReport = combined""",
"""        if (depthSourceVerdict.blocksDirection) precisionDirectionTrustworthy = false
        val sparseMixedUnverified =
            jp.example.greenreader.precision.PrecisionFullDepthSupplementPolicy
                .suppressSparseMixedDirection(
                    rawPoints = depthSourceVerdict.raw.points,
                    rawFrames = depthSourceVerdict.raw.uniqueFrames,
                    fullPoints = depthSourceVerdict.full.points,
                    independentSourcesAgree = depthSourceVerdict.crossSourceVerified
                )
        if (sparseMixedUnverified) precisionDirectionTrustworthy = false

        consensusReport = combined""", "suppress unverified sparse mixed guidance")
m = one(m,
"""        precisionLastDiagnostic += " | " + depthSourceVerdict.diagnostic +
            " | " + directionVerdict.diagnostic +""",
"""        precisionLastDiagnostic += " | " + depthSourceVerdict.diagnostic +
            " | SPARSE_RAW_FULL_UNVERIFIED=" + sparseMixedUnverified +
            " | " + directionVerdict.diagnostic +""", "field telemetry")
m = one(m,
    """                    !depthSourceVerdict.blocksDirection
            )""",
    """                    !depthSourceVerdict.blocksDirection &&
                    !sparseMixedUnverified
            )""", "prevent high trust for sparse mixed sources")

if m.count("Precision 9.9") < 2:
    raise RuntimeError("v10.0 expected v9.9 app labels")
m = m.replace("Precision 9.9", "Precision 10.0")
g = one(g, 'versionName = "9.9"', 'versionName = "10.0"', "versionName")
g = one(g, "versionCode = 990", "versionCode = 1000", "versionCode")

test.write_text("""package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionSparseRawFallbackTest {
    private fun plan(rawPoints: Int, maxDepth: Float = 5f) =
        PrecisionFullDepthSupplementPolicy.plan(
            rawAccepted = rawPoints > 0,
            requestedMinDepthM = 0.25f,
            requestedMaxDepthM = maxDepth,
            ballAxialDepthM = 2.96f,
            rawPointsInFrame = rawPoints
        )

    @Test fun fieldSparseRawAlwaysRequestsFullEvidence() {
        for (n in listOf(0, 1, 8, 14, 16, 80, 103, 159)) {
            assertTrue("Raw=$n", plan(n).useFull)
            assertEquals(0.25f, plan(n).minDepthM, 0.001f)
        }
    }

    @Test fun denseRawRemainsRawOnlyForShortPutt() {
        for (n in listOf(160, 384, 399, 439, 453)) {
            assertFalse("Raw=$n", plan(n).useFull)
        }
    }

    @Test fun longRangeDenseRawStillUsesDistanceLimitedFullSupplement() {
        assertTrue(plan(439, 6.97f).useFull)
        assertEquals(2.46f, plan(439, 6.97f).minDepthM, 0.001f)
        assertEquals(0.25f, plan(16, 6.97f).minDepthM, 0.001f)
    }

    @Test fun sparseMixedRawCannotCertifyDirectionWithoutAgreement() {
        val policy = PrecisionFullDepthSupplementPolicy
        assertTrue(policy.suppressSparseMixedDirection(2455, 163, 60000, false))
        assertTrue(policy.suppressSparseMixedDirection(12618, 156, 60000, false))
        assertFalse(policy.suppressSparseMixedDirection(43463, 99, 60000, false))
        assertFalse(policy.suppressSparseMixedDirection(2455, 163, 60000, true))
        assertFalse(policy.suppressSparseMixedDirection(2455, 163, 100, false))
        assertFalse(policy.suppressSparseMixedDirection(80, 1, 60000, false))
        assertFalse(policy.suppressSparseMixedDirection(0, 150, 60000, false))
    }
}
""", encoding="utf8")

# Safety invariant: ground decisions and real slope thresholds are untouched.
assert 'PrecisionAnchoredGroundSelector.select(' in (root / "precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root / "field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m
assert 'button("結果入力")' in m

policy.write_text(p, encoding="utf8")
collector.write_text(c, encoding="utf8")
main.write_text(m, encoding="utf8")
gradle.write_text(g, encoding="utf8")
print("v10.0: sparse Raw supplementation, per-frame density telemetry and fail-closed mixed-source directional trust")
