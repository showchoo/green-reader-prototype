"""Precision v8.1: compare fitted cross slope against paired left/right turf heights.

The independent check uses only accepted ground cells and matches the same
forward-distance slices. It is a veto against a strongly contradictory estimate,
not a device calibration or proof of ground-truth accuracy.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
policy=root/"precision/PrecisionPairedFlankAudit.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(src,old,new,label):
    n=src.count(old)
    if n != 1: raise SystemExit("v8.1 "+label+" found "+str(n))
    return src.replace(old,new,1)

policy.write_text('''package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Independent, non-fitting left/right height-difference verification:
 * each forward-distance bin compares symmetric flanks of accepted turf cells.
 * With a genuinely linear side slope, delta(height) / delta(side) has the
 * same sign as the regression's dH/dRight.
 *
 * A reliable opposite sign blocks drawing. A lack of lateral coverage
 * is INCONCLUSIVE and never pretends that the slope was verified.
 */
object PrecisionPairedFlankAudit {
    data class Verdict(
        val reason: String,
        val blocksDirection: Boolean,
        val verifiedAgreement: Boolean,
        val validSlices: Int,
        val opposingSlices: Int,
        val medianPairedCrossPercent: Float?
    ) {
        val diagnostic: String get() =
            "FLANK_AUDIT " + reason + " slices=" + validSlices +
                " opposite=" + opposingSlices +
                " pairedCross=" + (medianPairedCrossPercent?.let {
                    String.format(java.util.Locale.US, "%.2f", it)
                } ?: "NA")
    }

    private const val SLICES = 8
    private const val MIN_CELLS_PER_SIDE = 4
    private const val MIN_VALID_SLICES = 4
    private const val SIGNIFICANT_CROSS_PP = 1.2f
    private const val MIN_LATERAL_SEPARATION_M = 0.24f

    private data class Sample(val along: Float, val lateral: Float, val height: Float)

    private fun median(values: List<Float>): Float {
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 != 0) sorted[middle]
            else (sorted[middle - 1] + sorted[middle]) * 0.5f
    }

    /** Derived from independent physical side-to-side height differences. */
    fun evaluate(
        cells: List<PrecisionSurfaceCell>,
        ball: Vec3,
        cup: Vec3,
        reportedCrossPercent: Float?
    ): Verdict {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val d = sqrt(dx * dx + dz * dz)
        if (!d.isFinite() || d < 0.4f || reportedCrossPercent == null ||
            !reportedCrossPercent.isFinite() ||
            abs(reportedCrossPercent) < SIGNIFICANT_CROSS_PP) {
            return Verdict("NO_DIRECTION_TO_AUDIT", false, false, 0, 0, null)
        }
        val fx = dx / d
        val fz = dz / d
        val rx = -fz
        val rz = fx

        // Keep each distance bin independent: an overall height gradient
        // along the putt cannot masquerade as a sideways height gradient.
        val left = Array(SLICES) { ArrayList<Sample>() }
        val right = Array(SLICES) { ArrayList<Sample>() }
        for (cell in cells) {
            val x = cell.x - ball.x
            val z = cell.z - ball.z
            val along = x * fx + z * fz
            if (!along.isFinite() || along < 0f || along >= d) continue
            val lateral = x * rx + z * rz
            if (!lateral.isFinite() || !cell.height.isFinite()) continue
            val bucket = ((along / d) * SLICES).toInt().coerceIn(0, SLICES - 1)
            val sample = Sample(along, lateral, cell.height)
            when {
                lateral in -0.55f..-0.14f -> left[bucket].add(sample)
                lateral in 0.14f..0.55f -> right[bucket].add(sample)
            }
        }

        val slopes = ArrayList<Float>(SLICES)
        var opposing = 0
        var agreeing = 0
        for (i in 0 until SLICES) {
            val l = left[i]
            val r = right[i]
            if (l.size < MIN_CELLS_PER_SIDE || r.size < MIN_CELLS_PER_SIDE) continue
            // A forward-height gradient can mimic sideways grade if left
            // and right were observed at different distances along the
            // putt. Refuse that non-matched comparison.
            val ds = abs(median(l.map { it.along }) -
                median(r.map { it.along }))
            if (ds > 0.05f) continue
            val dl = median(l.map { it.lateral })
            val dr = median(r.map { it.lateral })
            val gap = dr - dl
            if (!gap.isFinite() || gap < MIN_LATERAL_SEPARATION_M) continue
            val h = median(r.map { it.height }) - median(l.map { it.height })
            val slope = h / gap * 100f
            if (!slope.isFinite()) continue
            slopes.add(slope)
            if (abs(slope) >= SIGNIFICANT_CROSS_PP) {
                if (slope * reportedCrossPercent < 0f) opposing++
                else agreeing++
            }
        }

        val m = if (slopes.isNotEmpty()) median(slopes) else null
        if (slopes.size < MIN_VALID_SLICES) {
            return Verdict("INSUFFICIENT_PAIRED_COVERAGE", false, false, slopes.size, opposing, m)
        }
        // At least 75% of all valid slices must contradict the fitted slope,
        // including at least three truly significant opposite slices.
        if (opposing >= 3 && opposing * 4 >= slopes.size * 3 &&
            m != null && abs(m) >= SIGNIFICANT_CROSS_PP &&
            m * reportedCrossPercent < 0f) {
            return Verdict("OPPOSITE_PAIRED_HEIGHTS", true, false, slopes.size, opposing, m)
        }
        // Opposing local slopes may be genuine complex greens. Leave them
        // inconclusive unless the directional consistency is very strong.
        val verified = agreeing >= 4 && agreeing * 4 >= slopes.size * 3 &&
            m != null && abs(m) >= SIGNIFICANT_CROSS_PP &&
            m * reportedCrossPercent > 0f
        return Verdict(
            if (verified) "PAIRED_HEIGHTS_AGREE" else "MIXED_OR_WEAK_PAIRED_HEIGHTS",
            false, verified, slopes.size, opposing, m
        )
    }
}
''',encoding="utf8")

s=one(s,
'''        if (depthSourceVerdict.blocksDirection) precisionDirectionTrustworthy = false

        consensusReport = combined
        precisionLastDiagnostic += " | " + depthSourceVerdict.diagnostic +''',
'''        if (depthSourceVerdict.blocksDirection) precisionDirectionTrustworthy = false

        // A second, inexpensive method checks matched heights on either side
        // of the putt. It can expose a coherent wrong-sign regression even
        // if Raw and Full happen to agree with each other.
        val flankVerdict = jp.example.greenreader.precision.PrecisionPairedFlankAudit.evaluate(
            aggregateSurface?.cells.orEmpty(), marks.first, marks.second,
            combined?.overallCrossPercent
        )
        if (flankVerdict.blocksDirection ||
            precisionMarkerGeometry()?.needsReview == true) {
            precisionDirectionTrustworthy = false
        }

        consensusReport = combined
        precisionLastDiagnostic += " | " + flankVerdict.diagnostic +
            " | " + depthSourceVerdict.diagnostic +''',
"matched flank veto + marker trust for rendering")

s=one(s,
'''                    !depthSourceVerdict.blocksDirection
            )''',
'''                    !depthSourceVerdict.blocksDirection &&
                    !flankVerdict.blocksDirection
            )''',
"quality cap on paired-flank sign conflict")

assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert 'button("次のホール")' in s
assert 'button("結果入力")' in s
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
if 'Precision 8.0' not in s: raise SystemExit("v8.0 source version missing")
s=s.replace("Precision 8.0","Precision 8.1")
g=one(g,'versionName = "8.0"','versionName = "8.1"',"name")
g=one(g,'versionCode = 800','versionCode = 810',"code")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied Precision v8.1 paired flank direction audit")
