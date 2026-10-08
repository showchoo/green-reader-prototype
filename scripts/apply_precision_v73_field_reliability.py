"""v7.3: retain all v7.1 field features; fix corrupt JSON and incomplete diagnostics.

M07 field evidence: 52 scans, including 20 slope-limit rejects. Do NOT loosen
the 12% slope gate or pretend a high quality score proves absolute accuracy.
"""
from pathlib import Path
import re

main_path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
rec_path = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt")
quality_path = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionQualityEstimator.kt")
analyzer_path = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt")
gradle_path = Path("app/build.gradle.kts")
s = main_path.read_text(encoding="utf-8")
r = rec_path.read_text(encoding="utf-8")
q = quality_path.read_text(encoding="utf-8")
a = analyzer_path.read_text(encoding="utf-8")
g = gradle_path.read_text(encoding="utf-8")

def replace_one(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"v7.3 {label}: expected one match, found {count}")
    return source.replace(old, new, 1)

# JSON escaping was written for regular Kotlin strings inside raw triple-quoted
# literals. In the resulting files, field names were literally \"field\" and
# neither failure nor success metadata was valid JSON. Only unescape the two
# raw JSON payload templates; retain escaping for interpolated user text.
for function_name in ("metadataJson", "failureMetadataJson"):
    fpos = r.index("private fun " + function_name + "(")
    start = r.index('return """{', fpos)
    stop = r.index('"""', start + len('return """'))
    template = r[start:stop]
    count = template.count(r'\"')
    if count < 10:
        raise SystemExit(f"v7.3 {function_name}: JSON escape bug not found")
    fixed = template.replace(r'\"', '"')
    r = r[:start] + fixed + r[stop:]
    assert r[start:stop].count(r'\"') == 0

# Snapshot diagnostics are captured for each scan window before its collector is
# reset. The old recorder accidentally logged the *cleared* collector (all 0s).
summary_helper = r'''    private fun precisionFieldCollectorSummary(): String {
        val snapshots = precisionCollectorWindowSnapshots.toMutableList()
        val active = precisionCollector.diagnosticSnapshot()
        if (active.attemptedFrames > 0 || active.pointCount > 0) snapshots.add(active)
        val total = jp.example.greenreader.precision.PrecisionDepthCollector.DiagnosticsSnapshot.aggregate(snapshots)
        return "windows=" + snapshots.size +
            " attempts=" + total.attemptedFrames +
            " rawFrames=" + total.rawAcquiredFrames +
            " fullFrames=" + total.fullAcquiredFrames +
            " rawNonZero=" + total.rawNonZeroPixels +
            " fullNonZero=" + total.fullNonZeroPixels +
            " confPass=" + total.confidencePassedPixels +
            " acceptedFrames=" + total.acceptedUniqueFrames +
            " rawAcceptedFrames=" + total.rawAcceptedFrames +
            " fullAcceptedFrames=" + total.fullAcceptedFrames +
            " duplicateRaw=" + total.duplicateRawFrames +
            " duplicateFull=" + total.duplicateFullFrames +
            " points=" + total.pointCount +
            " transformedValid=" + total.transformedValidPoints +
            " notYet=" + total.notYetAvailableCount +
            " errors=" + total.otherErrorCount +
            " quality=" + (precisionCurrentQuality?.summary() ?: "-")
    }

'''
anchor = "    private fun updatePrecisionRecordLabel() {"
if s.count(anchor) != 1:
    raise SystemExit("v7.3 record helper insertion point missing")
s = s.replace(anchor, summary_helper + anchor, 1)
diag_count = s.count("precisionCollector.diagnosticSummary()")
if diag_count < 2:
    raise SystemExit(f"v7.3 expected at least two old cleared diagnostics, got {diag_count}")
s = s.replace("precisionCollector.diagnosticSummary()", "precisionFieldCollectorSummary()")

# The final complete W1...W8 + aggregate analysis must be saved even if
# capture/overlay generation later resets precisionLastDiagnostic to MARK.
s = replace_one(
    s,
    "    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null",
    """    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null
    private var precisionCompletedDiagnostic = ""
    private var precisionLastScanFailed = false""",
    "persistent final diagnostic fields"
)

# One assignment per scan resets stale success/failure status and snapshots.
pattern = re.compile(r"(?m)^([ \t]*)precisionCurrentQuality = null$")
s, reset_count = pattern.subn(
    lambda m: m.group(0) + "\n" + m.group(1) +
              'precisionCompletedDiagnostic = ""' + "\n" + m.group(1) +
              "precisionLastScanFailed = false",
    s
)
if reset_count < 2:
    raise SystemExit(f"v7.3 expected quality resets, saw {reset_count}")

# Freeze the successful aggregate before subsequent UI requests can modify
# precisionLastDiagnostic. All eight segment fit diagnostics are preserved.
s = replace_one(
    s,
    '''        precisionCurrentQuality?.let { quality ->
            precisionLastDiagnostic += " | QUALITY: " + quality.summary()
            updatePrecisionRecordLabel()
        }

        if (combined == null && consensusWindowIndex < precisionMaxWindows) {''',
    '''        precisionCurrentQuality?.let { quality ->
            precisionLastDiagnostic += " | QUALITY: " + quality.summary()
            updatePrecisionRecordLabel()
        }
        if (combined != null) {
            precisionCompletedDiagnostic = precisionLastDiagnostic
        }

        if (combined == null && consensusWindowIndex < precisionMaxWindows) {''',
    "persist final detailed diagnostics"
)
s = s.replace(
    "precisionDiagnostic = precisionLastDiagnostic,",
    "precisionDiagnostic = precisionCompletedDiagnostic.ifBlank { precisionLastDiagnostic },"
)
if s.count("precisionCompletedDiagnostic.ifBlank") < 2:
    raise SystemExit("v7.3 expected grouped and fallback successful saves")

# Developer trace: include complete surface and local-segment decisions
# even when aggregate analysis succeeded (previously only overall slopes).
s = replace_one(
    s,
    '''                " cross=" + String.format("%.2f", aggregateReport.overallCrossPercent)
''',
    '''                " cross=" + String.format("%.2f", aggregateReport.overallCrossPercent) +
                " surface=[" + PrecisionSurfaceBuilder.lastDiagnostic + "]" +
                " analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"
''',
    "aggregate success per-segment diagnostics"
)

# Never show score/uncertainty as if a measurement succeeded after a failure.
s = replace_one(
    s,
    '''    private fun recordPrecisionScanFailure(message: String) {
        val detail =''',
    '''    private fun recordPrecisionScanFailure(message: String) {
        precisionLastScanFailed = true
        val detail =''',
    "failure status"
)
s = replace_one(
    s,
    '''        val qualityText = if (q == null) {
            "測定信頼度 --"
        } else {''',
    '''        val qualityText = if (precisionLastScanFailed) {
            "測定不成立  /  再スキャンしてください"
        } else if (q == null) {
            "測定信頼度 --"
        } else {''',
    "failure before quality label"
)
s = replace_one(
    s,
    r'''                "\n推定誤差 ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%"''',
    r'''                "\n推定ばらつき ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%（参考値）"''',
    "uncertainty transparency"
)

# The quality ranking must not be HIGH when no independent window agrees and
# must not remain STANDARD when no valid slope analysis was produced.
q = replace_one(
    q,
    '''        val tier = when {
            score >= 85 && uncertainty <= 0.40f && corridorCoverage >= 0.875f ->''',
    '''        val tier = when {
            report == null -> TIER_LOW_CONFIDENCE
            score >= 85 && windowReports.size >= 2 &&
                uncertainty <= 0.40f && corridorCoverage >= 0.875f ->''',
    "reject invalid analysis and unverified high tier"
)

# Fix Kotlin precedence in slope rejection diagnostic string: previously the
# "valid", "fitMissing", and rejected segment counts were omitted if a global
# plane existed.
a = replace_one(
    a,
    '''            " global=" + if (globalForward != null && globalRight != null) {
                String.format("%.1f/%.1f/%.1f", globalForward, globalRight, globalTotal)
            } else "null" +
            " valid=" + segments.size + "/" + segmentCount +''',
    '''            " global=" + (if (globalForward != null && globalRight != null) {
                String.format("%.1f/%.1f/%.1f", globalForward, globalRight, globalTotal)
            } else "null") +
            " valid=" + segments.size + "/" + segmentCount +''',
    "full segment rejection counters"
)

# Increment version after applying the actual v7.2 UI patch.
if "Precision 7.2" not in s:
    raise SystemExit("v7.3 source version target missing; v7.2 UI was not applied")
s = s.replace("Precision 7.2", "Precision 7.3")
g = replace_one(g, 'versionName = "7.2"', 'versionName = "7.3"', "version name")
g = replace_one(g, 'versionCode = 720', 'versionCode = 730', "version code")

assert 'button("結果入力")' in s
assert 'button("次のホール")' in s
assert 'bitmap = failureBitmap' in s
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in a
assert "MAX_LOCAL_RMSE_METERS = 0.040" in a
assert '  "schema_version":' in r

main_path.write_text(s, encoding="utf-8")
rec_path.write_text(r, encoding="utf-8")
quality_path.write_text(q, encoding="utf-8")
analyzer_path.write_text(a, encoding="utf-8")
gradle_path.write_text(g, encoding="utf-8")
print("Applied Precision v7.3 M07 field diagnostics and JSON repairs")
