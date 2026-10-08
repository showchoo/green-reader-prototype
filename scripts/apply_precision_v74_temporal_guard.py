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

helper=r'''    private fun precisionTemporalSlopeCheck(): Pair<Boolean, String> {
        val usable = precisionWindowGlobalSlopes.filterNotNull()
        val series = precisionWindowGlobalSlopes.mapIndexed { index, slope ->
            if (slope == null) "W${index + 1}=NA" else
                "W${index + 1}=" +
                    String.format(java.util.Locale.US, "%.2f/%.2f", slope.first, slope.second)
        }.joinToString(",")
        if (usable.size < 4) {
            return Pair(false,
                "TEMPORAL insufficient global_windows=${usable.size}/${precisionWindowGlobalSlopes.size} series=[$series]")
        }
        fun median(values: List<Float>): Float {
            val sorted = values.sorted()
            val index = sorted.size / 2
            return if (sorted.size % 2 == 1) sorted[index]
                else (sorted[index - 1] + sorted[index]) / 2f
        }
        val splitAt = usable.size / 2
        val early = usable.subList(0, splitAt)
        val late = usable.subList(splitAt, usable.size)
        val deltaLong = median(early.map { it.first }) - median(late.map { it.first })
        val deltaCross = median(early.map { it.second }) - median(late.map { it.second })
        val disagreement = kotlin.math.sqrt(deltaLong * deltaLong + deltaCross * deltaCross)
        val unstable = !disagreement.isFinite() || disagreement > 2.5f
        return Pair(unstable,
            "TEMPORAL global_windows=${usable.size}/${precisionWindowGlobalSlopes.size}" +
                " early_late_delta_pp=" +
                String.format(java.util.Locale.US, "%.2f", disagreement) +
                " state=" + (if (unstable) "UNSTABLE" else "STABLE") +
                " series=[$series]")
    }

'''
marker="    private fun updatePrecisionRecordLabel() {"
if s.count(marker)!=1:raise SystemExit("v7.4 temporal helper insertion point missing")
s=s.replace(marker,helper+marker,1)

s=once(
'''        val combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined

        precisionCurrentQuality =''',
'''        var combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        val temporalResult = precisionTemporalSlopeCheck()
        val precisionTemporalUnstable = combined != null && temporalResult.first
        if (precisionTemporalUnstable) combined = null
        consensusReport = combined
        precisionLastDiagnostic += " | " + temporalResult.second +
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

main_path.write_text(s,encoding="utf-8")
analyzer_path.write_text(a,encoding="utf-8")
gradle_path.write_text(g,encoding="utf-8")
print("Applied Precision v7.4 temporal slope guard and full-window reservoir")
