"""Green Reader Precision v10.5: independently report Raw/Full forward AND cross slopes.

The existing source-veto reconstruction already builds separate surfaces but
only logs cross slope and refuses to estimate when the *other* source is sparse.
This diagnostic extension exposes each source's two signed derivatives, cells
and RMS independently without weakening any production acceptance or trust
decision. No mixed point cloud is used for the source-only figures.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
source=root/"precision/PrecisionDepthSourceAudit.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
s=source.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(x,old,new,tag):
    c=x.count(old)
    if c!=1: raise RuntimeError(f"v10.5 {tag} expected once; got {c}")
    return x.replace(old,new,1)

s=one(s,
'''        val rmseMm: Float?
    )''',
'''        val rmseMm: Float?,
        val longitudinalPercent: Float? = null
    )''',
"add longitudinal fit to source estimate")

s=one(s,
'''                " fullP=" + full.points + " fullF=" + full.uniqueFrames +
                " fullSlope=" + (full.crossPercent?.let { String.format(java.util.Locale.US, "%.2f", it) } ?: "NA")''',
'''                " fullP=" + full.points + " fullF=" + full.uniqueFrames +
                " fullSlope=" + (full.crossPercent?.let { String.format(java.util.Locale.US, "%.2f", it) } ?: "NA") +
                // These fields are observational, never a claim of true green slope.
                " | INDEPENDENT_SOURCE_SLOPES_V1" +
                " rawLongPct=" + (raw.longitudinalPercent?.let {
                    String.format(java.util.Locale.US, "%.2f",it) } ?: "NA") +
                " rawCrossPct=" + (raw.crossPercent?.let {
                    String.format(java.util.Locale.US, "%.2f",it) } ?: "NA") +
                " rawGroundCells=" + raw.groundCells +
                " rawRmseMm=" + (raw.rmseMm?.let {
                    String.format(java.util.Locale.US, "%.1f",it) } ?: "NA") +
                " fullLongPct=" + (full.longitudinalPercent?.let {
                    String.format(java.util.Locale.US, "%.2f",it) } ?: "NA") +
                " fullCrossPct=" + (full.crossPercent?.let {
                    String.format(java.util.Locale.US, "%.2f",it) } ?: "NA") +
                " fullGroundCells=" + full.groundCells +
                " fullRmseMm=" + (full.rmseMm?.let {
                    String.format(java.util.Locale.US, "%.1f",it) } ?: "NA") +
                " deltaLongPp=" + (if (raw.longitudinalPercent != null &&
                    full.longitudinalPercent != null)
                    String.format(java.util.Locale.US,"%.2f",
                        kotlin.math.abs(raw.longitudinalPercent-full.longitudinalPercent))
                    else "NA") +
                " deltaCrossPp=" + (if (raw.crossPercent != null &&
                    full.crossPercent != null)
                    String.format(java.util.Locale.US,"%.2f",
                        kotlin.math.abs(raw.crossPercent-full.crossPercent))
                    else "NA") +
                " diagnosticOnly=true independentGroundTruth=false"''',
"report independently fitted slopes in existing archived source diagnostics")

s=one(s,
'''        if (rawCount < MIN_POINTS || fullCount < MIN_POINTS ||
            rawFrames.size < MIN_FRAMES || fullFrames.size < MIN_FRAMES) {
            return judge(reportedCross, null, null,
                rawCount, fullCount, rawFrames.size, fullFrames.size)
        }

        // A deterministic stride cap keeps both reconstructions bounded.''',
'''        // An individual source may be independently measurable even when the
        // OTHER source is missing. Preserve the original dual-source veto
        // behavior but do not hide a usable single-source diagnostic.

        // A deterministic stride cap keeps both reconstructions bounded.''',
"allow independent fit when other source is weak")

s=one(s,
'''            val cross = if (fit != null && fit.samples >= MIN_CELLS &&
                mm != null && mm.isFinite() && mm <= MAX_RMSE_MM) {
                (fit.dHdRight * 100.0).toFloat().takeIf { it.isFinite() }
            } else null
            return Estimate(cross, total, frames, surface.groundCellCount, mm)
        }

        return compare(
            reportedCross,
            estimate("raw", rawCount, rawFrames.size),
            estimate("full", fullCount, fullFrames.size)
        )''',
'''            val usable = fit != null && fit.samples >= MIN_CELLS &&
                mm != null && mm.isFinite() && mm <= MAX_RMSE_MM
            val cross = if (usable) (fit!!.dHdRight * 100.0).toFloat()
                .takeIf { it.isFinite() } else null
            val longitudinal = if (usable) (fit!!.dHdForward * 100.0).toFloat()
                .takeIf { it.isFinite() } else null
            return Estimate(cross, total, frames, surface.groundCellCount, mm,
                longitudinalPercent = longitudinal)
        }

        // Reconstruct each available source on its own ground surface.
        val raw = if (rawCount >= MIN_POINTS && rawFrames.size >= MIN_FRAMES)
            estimate("raw",rawCount,rawFrames.size)
        else Estimate(null,rawCount,rawFrames.size,0,null)
        val full = if (fullCount >= MIN_POINTS && fullFrames.size >= MIN_FRAMES)
            estimate("full",fullCount,fullFrames.size)
        else Estimate(null,fullCount,fullFrames.size,0,null)

        // A missing second source must never certify or veto direction.
        if (rawCount < MIN_POINTS || fullCount < MIN_POINTS ||
            rawFrames.size < MIN_FRAMES || fullFrames.size < MIN_FRAMES) {
            return Verdict("INSUFFICIENT_DUAL_SOURCE", false, false,raw,full)
        }
        return compare(reportedCross,raw,full)''',
"calculate both derivatives and keep independent scant-source report")

# v10.5's full-source diagnostics intentionally append to the same
# precisionLastDiagnostic that is archived on success and failure.
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'depthSourceVerdict.diagnostic' in m
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'PrecisionDepthFreshnessPolicy.evaluate(frame.timestamp, timestamp)' in (
    root/"precision/PrecisionDepthCollector.kt").read_text()
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()

source.write_text(s,encoding="utf8")
print("v10.5 independent Raw/Full longitudinal/cross slope telemetry without veto changes")
