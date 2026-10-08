"""v7.4: retain late Depth frames and check global-slope stability across scan windows.

Changes measurement safety and sampling only, not the 12% slope rejection.
"""
from pathlib import Path
import re

main_path=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
analyzer_path=Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt")
gradle_path=Path("app/build.gradle.kts")
s=main_path.read_text(encoding="utf-8")
a=analyzer_path.read_text(encoding="utf-8")
g=gradle_path.read_text(encoding="utf-8")

def once(old,new,label,src):
    n=src.count(old)
    if n!=1: raise SystemExit(f"v7.4 {label}: expected one match, found {n}")
    return src.replace(old,new,1)

a=once(
'''    @Volatile var lastDiagnostic: String = ""
        private set''',
'''    @Volatile var lastDiagnostic: String = ""
        private set

    // The global plane is already fit for each window, even if local parts fail.
    @Volatile var lastGlobalSlopePercent: Pair<Float, Float>? = null
        private set''',
"global diagnostic property",a)
a=once(
'''    ): SlopeReport? {
        val dx = cup.x - ball.x''',
'''    ): SlopeReport? {
        lastGlobalSlopePercent = null
        val dx = cup.x - ball.x''',
"clear global diagnostic",a)
a=once(
'''        val segments = ArrayList<SlopeSegment>()''',
'''        lastGlobalSlopePercent =
            if (globalForward != null && globalRight != null &&
                globalForward.isFinite() && globalRight.isFinite()) {
                Pair(globalForward, globalRight)
            } else null

        val segments = ArrayList<SlopeSegment>()''',
"capture wide slope",a)

s=once(
'''    private val precisionCollectorWindowSnapshots =
        ArrayList<jp.example.greenreader.precision.PrecisionDepthCollector.DiagnosticsSnapshot>(8)''',
'''    private val precisionCollectorWindowSnapshots =
        ArrayList<jp.example.greenreader.precision.PrecisionDepthCollector.DiagnosticsSnapshot>(8)

    // Window-wide slope already calculated by the normal analyzer.
    private val precisionWindowGlobalSlopes = ArrayList<Pair<Float, Float>?>(8)

    // Reservoir keeps every time interval represented under the 90k-point cap.
    private var precisionLogPointsSeen = 0
    private val precisionReservoirRandom = java.util.Random(20261008L)''',
"temporal and reservoir state",s)

pat=re.compile(r"(?m)^([ \t]*)precisionLogPoints.clear\(\)$")
def reset(m):
    indent=m.group(1)
    return (m.group(0)+"\n"+indent+"precisionLogPointsSeen = 0"+
            "\n"+indent+"precisionReservoirRandom.setSeed(20261008L)"+
            "\n"+indent+"precisionWindowGlobalSlopes.clear()")
s,n=pat.subn(reset,s)
if n<2:raise SystemExit(f"v7.4 expected >=2 scan state resets, got {n}")

s=once(
'''        val precisionRoom = (90000 - precisionLogPoints.size).coerceAtLeast(0)
        if (precisionRoom > 0 && precisionPoints.isNotEmpty()) {
            val keep = if (precisionPoints.size <= precisionRoom) precisionPoints else precisionPoints.takeLast(precisionRoom)
            precisionLogPoints.addAll(keep)
        }
''',
'''        // Uniform deterministic reservoir avoids excluding last scan windows.
        for (sample in precisionPoints) {
            precisionLogPointsSeen += 1
            if (precisionLogPoints.size < 90000) {
                precisionLogPoints.add(sample)
            } else {
                val at = precisionReservoirRandom.nextInt(precisionLogPointsSeen)
                if (at < 90000) precisionLogPoints[at] = sample
            }
        }
''',
"remove early-window point cap",s)

s=once(
'''        val candidate = precisionCandidate
''',
'''        // Save the global window estimate before the next window resets.
        precisionWindowGlobalSlopes.add(
            if (precisionPoints.size >= 250) {
                PrecisionSlopeAnalyzer.lastGlobalSlopePercent
            } else null
        )
        val candidate = precisionCandidate
''',
"record each window global",s)

helper = ""

marker="    private fun updatePrecisionRecordLabel() {"
if s.count(marker)!=1:raise SystemExit("v7.4 temporal helper insertion point missing")
s=s.replace(marker,helper+marker,1)

s=once(
'''        val combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined

        precisionCurrentQuality =''',
'''        var combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        val temporalResult = jp.example.greenreader.precision.PrecisionTemporalConsistency.evaluate(precisionWindowGlobalSlopes)
        val precisionTemporalUnstable = combined != null && temporalResult.unstable
        if (precisionTemporalUnstable) combined = null
        consensusReport = combined
        precisionLastDiagnostic += " | " + temporalResult.diagnostic +
            " | RESERVOIR seen=" + precisionLogPointsSeen +
            " saved=" + precisionLogPoints.size

        precisionCurrentQuality =''',
"reject large window drift before reporting success",s)
s=once(
'''                recordPrecisionScanFailure("追加測定しても結果が安定しませんでした。もう一度スキャンしてください")''',
'''                recordPrecisionScanFailure(
                    if (precisionTemporalUnstable) {
                        "測定中に傾斜推定が変動しました。端末をゆっくり動かして再スキャンしてください"
                    } else {
                        "追加測定しても結果が安定しませんでした。もう一度スキャンしてください"
                    }
                )''',
"explain drift rejection",s)

assert 'MAX_USABLE_SLOPE_PERCENT = 12f' in a
assert 'MAX_LOCAL_RMSE_METERS = 0.040' in a
assert 'LOCAL_FIT_RADIUS_METERS = 0.32f' in a
assert 'precisionCompletedDiagnostic = precisionLastDiagnostic' in s
assert 'button("結果入力")' in s
assert 'bitmap = failureBitmap' in s
if 'Precision 7.3' not in s:raise SystemExit("v7.4 source version target missing")
s=s.replace("Precision 7.3","Precision 7.4")
g=once('versionName = "7.3"','versionName = "7.4"',"version name",g)
g=once('versionCode = 730','versionCode = 740',"version code",g)

temporal_path=Path("app/src/main/java/jp/example/greenreader/precision/PrecisionTemporalConsistency.kt")
temporal_path.write_text(r'''package jp.example.greenreader.precision

import kotlin.math.sqrt

/**
 * Cheap sanity check on independent window-wide planes.
 * This is NOT an accuracy estimate or a calibrated confidence interval.
 * Requires four fitted windows, otherwise marks stability as unverified.
 */
object PrecisionTemporalConsistency {
    data class Result(
        val unstable: Boolean,
        val verified: Boolean,
        val disagreementPp: Float,
        val validWindows: Int,
        val diagnostic: String
    )

    fun evaluate(
        windows: List<Pair<Float, Float>?>,
        thresholdPp: Float = 2.5f
    ): Result {
        val values = windows.filterNotNull().filter {
            it.first.isFinite() && it.second.isFinite()
        }
        val series = windows.mapIndexed { index, slope ->
            if (slope == null || !slope.first.isFinite() || !slope.second.isFinite()) {
                "W" + (index + 1) + "=NA"
            } else {
                "W" + (index + 1) + "=" +
                    String.format(java.util.Locale.US, "%.2f/%.2f", slope.first, slope.second)
            }
        }.joinToString(",")
        if (values.size < 4) {
            return Result(false, false, Float.NaN, values.size,
                "TEMPORAL insufficient global_windows=" + values.size + "/" + windows.size +
                    " series=[" + series + "]")
        }
        fun median(list: List<Float>): Float {
            val sorted = list.sorted()
            val at = sorted.size / 2
            return if (sorted.size % 2 == 1) sorted[at]
                else (sorted[at - 1] + sorted[at]) / 2f
        }
        val mid = values.size / 2
        val early = values.subList(0, mid)
        val late = values.subList(mid, values.size)
        val longitudinal = median(early.map { it.first }) - median(late.map { it.first })
        val cross = median(early.map { it.second }) - median(late.map { it.second })
        val disagreement = sqrt(longitudinal * longitudinal + cross * cross)
        val unstable = !disagreement.isFinite() || disagreement > thresholdPp
        return Result(
            unstable = unstable,
            verified = true,
            disagreementPp = disagreement,
            validWindows = values.size,
            diagnostic = "TEMPORAL global_windows=" + values.size + "/" + windows.size +
                " early_late_delta_pp=" +
                String.format(java.util.Locale.US, "%.2f", disagreement) +
                " state=" + (if (unstable) "UNSTABLE" else "STABLE") +
                " series=[" + series + "]"
        )
    }
}
''',encoding="utf-8")

main_path.write_text(s,encoding="utf-8")
analyzer_path.write_text(a,encoding="utf-8")
gradle_path.write_text(g,encoding="utf-8")
print("Applied Precision v7.4 temporal slope guard and full-window reservoir")
