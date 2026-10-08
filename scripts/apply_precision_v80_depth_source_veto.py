"""Precision 8.0: independently reconstruct Raw and Full depth cross slopes.

Only compare when BOTH depth sources have enough samples across frames.
Never invent an orientation or auto-flip all measured slopes. When both
credible estimates disagree, hide directional predictions but still save
the complete original scan.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
policy=root/"precision/PrecisionDepthSourceAudit.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit(f"v8.0 {label}: expected one match, got {n}")
    return src.replace(old,new,1)

policy.write_text('''package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Independent source audit. The normal aggregate estimator still determines
 * the numeric slope; this only checks whether rendering its DIRECTION is safe.
 * An unobserved/weak source must never be treated as positive confirmation.
 *
 * Running two additional surface reconstructions only when both source types
 * were sampled significantly avoids slowing most M07 scans.
 */
object PrecisionDepthSourceAudit {
    data class Estimate(
        val crossPercent: Float?,
        val points: Int,
        val uniqueFrames: Int,
        val groundCells: Int,
        val rmseMm: Float?
    )

    data class Verdict(
        val reason: String,
        val blocksDirection: Boolean,
        val crossSourceVerified: Boolean,
        val raw: Estimate,
        val full: Estimate
    ) {
        val diagnostic: String get() =
            "DEPTH_SOURCES " + reason +
                " rawP=" + raw.points + " rawF=" + raw.uniqueFrames +
                " rawSlope=" + (raw.crossPercent?.let { String.format(java.util.Locale.US, "%.2f", it) } ?: "NA") +
                " fullP=" + full.points + " fullF=" + full.uniqueFrames +
                " fullSlope=" + (full.crossPercent?.let { String.format(java.util.Locale.US, "%.2f", it) } ?: "NA")
    }

    private const val MIN_POINTS = 2200
    private const val MIN_FRAMES = 4
    private const val MAX_POINTS_PER_SOURCE = 25000
    private const val MIN_CELLS = 40
    private const val MAX_RMSE_MM = 30f
    private const val SIGNIFICANT_CROSS_PP = 0.8f
    private const val MAX_SOURCE_DIFFERENCE_PP = 3.0f

    fun judge(
        reportedCross: Float?,
        rawCross: Float?,
        fullCross: Float?,
        rawPoints: Int,
        fullPoints: Int,
        rawFrames: Int,
        fullFrames: Int
    ): Verdict {
        val raw = Estimate(rawCross, rawPoints, rawFrames, 0, null)
        val full = Estimate(fullCross, fullPoints, fullFrames, 0, null)
        val enough = rawPoints >= MIN_POINTS && fullPoints >= MIN_POINTS &&
            rawFrames >= MIN_FRAMES && fullFrames >= MIN_FRAMES
        if (!enough) return Verdict("INSUFFICIENT_DUAL_SOURCE", false, false, raw, full)
        return compare(reportedCross, raw, full)
    }

    private fun compare(reportedCross: Float?, raw: Estimate, full: Estimate): Verdict {
        val r = raw.crossPercent
        val f = full.crossPercent
        if (r == null || f == null || !r.isFinite() || !f.isFinite()) {
            return Verdict("SOURCE_FIT_UNRESOLVED", true, false, raw, full)
        }
        if (abs(r) < SIGNIFICANT_CROSS_PP || abs(f) < SIGNIFICANT_CROSS_PP) {
            // A positive aggregate direction may be supported by only one
            // source; don't endorse it when another substantial source is flat.
            return Verdict("WEAK_SOURCE_DIRECTION", true, false, raw, full)
        }
        if (r * f < 0f) return Verdict("OPPOSITE_RAW_FULL", true, false, raw, full)
        if (abs(r - f) > MAX_SOURCE_DIFFERENCE_PP) {
            return Verdict("RAW_FULL_MAGNITUDE_DISAGREEMENT", true, false, raw, full)
        }
        if (reportedCross == null || !reportedCross.isFinite() ||
            abs(reportedCross) < SIGNIFICANT_CROSS_PP) {
            return Verdict("AGGREGATE_DIRECTION_WEAK", true, false, raw, full)
        }
        if (r * reportedCross < 0f || f * reportedCross < 0f) {
            return Verdict("SOURCES_OPPOSE_AGGREGATE", true, false, raw, full)
        }
        return Verdict("RAW_FULL_AGREE", false, true, raw, full)
    }

    fun analyze(
        points: List<PrecisionDepthPoint>,
        ball: Vec3,
        cup: Vec3,
        reportedCross: Float?
    ): Verdict {
        var rawCount = 0
        var fullCount = 0
        val rawFrames = HashSet<Long>()
        val fullFrames = HashSet<Long>()
        for (p in points) {
            if (p.depthSource == "raw") {
                rawCount++
                rawFrames += p.frameTimestampNs
            } else if (p.depthSource == "full") {
                fullCount++
                fullFrames += p.frameTimestampNs
            }
        }
        if (rawCount < MIN_POINTS || fullCount < MIN_POINTS ||
            rawFrames.size < MIN_FRAMES || fullFrames.size < MIN_FRAMES) {
            return judge(reportedCross, null, null,
                rawCount, fullCount, rawFrames.size, fullFrames.size)
        }

        // A deterministic stride cap keeps both reconstructions bounded.
        // The selected samples still represent the entire scan time range.
        fun collect(source: String, total: Int): List<PrecisionDepthPoint> {
            val keep = minOf(total, MAX_POINTS_PER_SOURCE)
            val out = ArrayList<PrecisionDepthPoint>(keep)
            var seen = 0
            for (point in points) {
                if (point.depthSource != source) continue
                if (out.size < keep && ((seen.toLong() + 1L) * keep / total) >
                    (seen.toLong() * keep / total)) {
                    out.add(point)
                }
                seen++
            }
            return out
        }

        fun estimate(source: String, total: Int, frames: Int): Estimate {
            val sampled = collect(source, total)
            val surface = PrecisionSurfaceBuilder.build(sampled, ball, cup)
            if (surface.groundCellCount < MIN_CELLS || surface.uniqueFrames < MIN_FRAMES) {
                return Estimate(null, total, frames, surface.groundCellCount, null)
            }
            val dx = cup.x - ball.x
            val dz = cup.z - ball.z
            val distance = sqrt(dx * dx + dz * dz)
            if (!distance.isFinite() || distance < 0.4f) {
                return Estimate(null, total, frames, surface.groundCellCount, null)
            }
            val fx = dx / distance
            val fz = dz / distance
            val rx = -fz
            val rz = fx
            val fit = PrecisionLocalQuadraticFitter.fit(
                surface.cells,
                ball.x + dx * 0.5f,
                ball.z + dz * 0.5f,
                fx, fz, rx, rz,
                radiusMeters = max(0.60f, distance * 0.75f)
            )
            val mm = fit?.rmseMeters?.times(1000.0)?.toFloat()
            val cross = if (fit != null && fit.samples >= MIN_CELLS &&
                mm != null && mm.isFinite() && mm <= MAX_RMSE_MM) {
                (fit.dHdRight * 100.0).toFloat().takeIf { it.isFinite() }
            } else null
            return Estimate(cross, total, frames, surface.groundCellCount, mm)
        }

        return compare(
            reportedCross,
            estimate("raw", rawCount, rawFrames.size),
            estimate("full", fullCount, fullFrames.size)
        )
    }
}
''',encoding="utf8")

s=one(s,
'''        precisionDirectionTrustworthy = directionVerdict.trustworthy
        consensusReport = combined
        precisionLastDiagnostic += " | " + directionVerdict.diagnostic +''',
'''        precisionDirectionTrustworthy = directionVerdict.trustworthy

        // Compare independently reconstructed Raw and Full slopes where both
        // sources contain meaningful ground coverage. Mixed-source consensus
        // alone cannot detect opposite-sign Depth bias.
        val depthSourceVerdict = jp.example.greenreader.precision.PrecisionDepthSourceAudit.analyze(
            precisionLogPoints, marks.first, marks.second, combined?.overallCrossPercent
        )
        if (depthSourceVerdict.blocksDirection) precisionDirectionTrustworthy = false

        consensusReport = combined
        precisionLastDiagnostic += " | " + depthSourceVerdict.diagnostic +
            " | " + directionVerdict.diagnostic +''',
"independent Raw/Full direction veto")

s=one(s,
'''                markerGeometryTrusted = precisionMarkerGeometry()?.needsReview != true
            )''',
'''                markerGeometryTrusted = precisionMarkerGeometry()?.needsReview != true &&
                    !depthSourceVerdict.blocksDirection
            )''',
"no high quality badge for opposing source fits")

assert 'button("次のホール")' in s
assert 'button("カップ再指定")' in s
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
if 'Precision 7.9' not in s:raise SystemExit("v7.9 must precede v8.0")
s=s.replace('Precision 7.9','Precision 8.0')
g=one(g,'versionName = "7.9"','versionName = "8.0"',"Gradle name")
g=one(g,'versionCode = 790','versionCode = 800',"Gradle code")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied Precision v8.0 independent Raw/Full direction audit")
