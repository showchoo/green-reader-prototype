"""Precision 8.3: fail closed on robust sign disagreement across spatial scales.

The same accepted ground surface is evaluated with 32cm (normal), 50cm,
and 80cm local support. Multi-scale disagreement is diagnostic evidence,
not new ground-truth measurement. Preserve baseline numeric slope.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
analyzer=root/"precision/PrecisionSlopeAnalyzer.kt"
audit=root/"precision/PrecisionScaleDirectionAudit.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
a=analyzer.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
def one(src,old,new,label):
    n=src.count(old)
    if n!=1:raise SystemExit(f"v8.3 {label}: expected 1 target, saw {n}")
    return src.replace(old,new,1)

a=one(a,
'''        segmentCount: Int = 8
    ): SlopeReport? {''',
'''        segmentCount: Int = 8,
        localFitRadiusMeters: Float = LOCAL_FIT_RADIUS_METERS
    ): SlopeReport? {''',
"add optional diagnostic-only radius")
a=one(a,
'''            val r2 = LOCAL_FIT_RADIUS_METERS * LOCAL_FIT_RADIUS_METERS''',
'''            val r2 = localFitRadiusMeters * localFitRadiusMeters''',
"radius-aware local count")
a=one(a,
'''                radiusMeters = LOCAL_FIT_RADIUS_METERS''',
'''                radiusMeters = localFitRadiusMeters''',
"radius-aware local fit")
# Keep same default for all existing callers; use a separate optional parameter
# only in the audit after the ordinary report has already been reconstructed.
audit.write_text('''package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs

/**
 * Spatial-scale stability test, not calibration.
 * Opposing credible signs between 32/50/80cm trigger a direction HOLD.
 * A curved green may genuinely change sign across lateral scales:
 * that is exactly when reporting a single left/right direction is unsafe.
 */
object PrecisionScaleDirectionAudit {
    data class Verdict(
        val reason: String,
        val blocksDirection: Boolean,
        val allScalesAgree: Boolean,
        val coreCross: Float?,
        val radius50Cross: Float?,
        val radius80Cross: Float?
    ) {
        val diagnostic: String get() =
            "SCALE_AUDIT " + reason + " cross32=" + fmt(coreCross) +
                " cross50=" + fmt(radius50Cross) +
                " cross80=" + fmt(radius80Cross)

        private fun fmt(v: Float?): String =
            v?.takeIf { it.isFinite() }?.let {
                String.format(java.util.Locale.US, "%.2f", it)
            } ?: "NA"
    }

    private const val MIN_SIGNIFICANT_CROSS_PP = 0.8f

    fun compare(core: Float?, radius50: Float?, radius80: Float?): Verdict {
        if (core == null || !core.isFinite() ||
            abs(core) < MIN_SIGNIFICANT_CROSS_PP) {
            return Verdict("UNRESOLVED_BASELINE", false, false, core, radius50, radius80)
        }
        fun strongSignConflict(value: Float?): Boolean =
            value != null && value.isFinite() &&
                abs(value) >= MIN_SIGNIFICANT_CROSS_PP && value * core < 0f

        if (strongSignConflict(radius50)) {
            return Verdict("RADIUS50_OPPOSITE", true, false, core, radius50, radius80)
        }
        if (strongSignConflict(radius80)) {
            return Verdict("RADIUS80_OPPOSITE", true, false, core, radius50, radius80)
        }
        val bothValid = radius50 != null && radius50.isFinite() &&
            radius80 != null && radius80.isFinite() &&
            abs(radius50) >= MIN_SIGNIFICANT_CROSS_PP &&
            abs(radius80) >= MIN_SIGNIFICANT_CROSS_PP
        return Verdict(
            if (bothValid) "SCALES_AGREE" else "SCALE_EVIDENCE_INCOMPLETE",
            false, bothValid, core, radius50, radius80
        )
    }

    fun evaluate(
        surface: PrecisionSurfaceModel?,
        ball: Vec3,
        cup: Vec3,
        baselineCross: Float?
    ): Verdict {
        if (surface == null || baselineCross == null ||
            !baselineCross.isFinite() ||
            abs(baselineCross) < MIN_SIGNIFICANT_CROSS_PP) {
            return compare(baselineCross, null, null)
        }
        val r50 = PrecisionSlopeAnalyzer.analyze(
            surface, ball, cup, localFitRadiusMeters = 0.50f
        )?.overallCrossPercent
        val r80 = PrecisionSlopeAnalyzer.analyze(
            surface, ball, cup, localFitRadiusMeters = 0.80f
        )?.overallCrossPercent
        return compare(baselineCross, r50, r80)
    }
}
''',encoding="utf8")

s=one(s,
'''        consensusReport = combined
        precisionLastDiagnostic += " | " + flankVerdict.diagnostic +''',
'''        // Reject an apparently stable 32cm cross slope if equally valid
        // 50cm/80cm neighborhoods infer the opposite direction.
        val scaleVerdict = jp.example.greenreader.precision.PrecisionScaleDirectionAudit.evaluate(
            aggregateSurface, marks.first, marks.second,
            aggregateReport?.overallCrossPercent
        )
        if (scaleVerdict.blocksDirection) precisionDirectionTrustworthy = false

        consensusReport = combined
        precisionLastDiagnostic += " | " + scaleVerdict.diagnostic +
            " | " + flankVerdict.diagnostic +''',
"spatial-scale audit at finalization")
s=one(s,
'''                    !flankVerdict.blocksDirection
            )''',
'''                    !flankVerdict.blocksDirection &&
                    !scaleVerdict.blocksDirection
            )''',
"high-quality cap on scale sign flip")

if 'Precision 8.2' not in s:raise SystemExit("v8.2 must precede v8.3")
s=s.replace("Precision 8.2","Precision 8.3")
g=one(g,'versionName = "8.2"','versionName = "8.3"',"version name")
g=one(g,'versionCode = 820','versionCode = 830',"version code")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in a
assert 'button("次のホール")' in s and 'button("結果入力")' in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert "PrecisionDepthSourceAudit.analyze(" in s
assert "precision_depth_sources.csv" in (root/"field/ScanFieldRecorder.kt").read_text()
main.write_text(s,encoding="utf8")
analyzer.write_text(a,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied v8.3 multi-radius direction safety audit")
