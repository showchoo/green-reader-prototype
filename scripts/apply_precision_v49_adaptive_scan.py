"""v6.9: adaptive scan acquisition — extend weak windows and retry automatically."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.9 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

# A 650 ms hard cut was too aggressive when ARCore Depth was warming up or
# delivering sparse Raw Depth. Keep the fast path identical when enough data
# exists, but allow a weak window to collect for up to 1.2 s.
once(
'''        if (now - consensusWindowStartedMs < 650L) return

        val points = collector.snapshot()
        val precisionPoints = precisionCollector.snapshot()
''',
'''        val precisionWindowElapsedMs = now - consensusWindowStartedMs
        val precisionWindowReady =
            precisionCollector.size() >= 250 && precisionCollector.uniqueFrames() >= 3
        if (precisionWindowElapsedMs < 650L) return
        if (!precisionWindowReady && precisionWindowElapsedMs < 1200L) return

        val points = collector.snapshot()
        val precisionPoints = precisionCollector.snapshot()
''',
"adaptive window duration"
)

# The old flow failed immediately after exactly five windows. Keep five as the
# normal target, but if aggregate/consensus is still not valid, collect up to
# three additional windows automatically before asking the user to rescan.
old_block='''        if (consensusWindowIndex < 5) {
            consensusWindowStartedMs = now
            runOnUiThread {
                if (scanning) status.text = "複数回測定中… " + precisionLastDiagnostic
            }
            return
        }

        val aggregateSurface = if (precisionLogPoints.size >= 500) {
            PrecisionSurfaceBuilder.build(precisionLogPoints, marks.first, marks.second)
        } else null
        precisionSurface = aggregateSurface
        val aggregateReport = aggregateSurface?.let {
            PrecisionSlopeAnalyzer.analyze(it, marks.first, marks.second)
        }
        val aggregateDiagnostic = if (aggregateSurface == null) {
            "AGG: points=" + precisionLogPoints.size + " surface=null"
        } else if (aggregateReport == null) {
            "AGG: rejected points=" + aggregateSurface.sourcePointCount +
                " frames=" + aggregateSurface.uniqueFrames +
                " ground=" + aggregateSurface.groundCellCount +
                " surface=[" + PrecisionSurfaceBuilder.lastDiagnostic +
                "] analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"
        } else {
            "AGG: OK points=" + aggregateSurface.sourcePointCount +
                " frames=" + aggregateSurface.uniqueFrames +
                " ground=" + aggregateSurface.groundCellCount +
                " long=" + String.format("%.2f", aggregateReport.overallLongitudinalPercent) +
                " cross=" + String.format("%.2f", aggregateReport.overallCrossPercent)
        }
        precisionLastDiagnostic =
            (precisionWindowDiagnostics + aggregateDiagnostic).joinToString(" | ")

        // Prefer one surface reconstructed from all five windows. Per-window
        // consensus remains only as a fallback for short putts/legacy behavior.
        val combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined
        scanning = false
        scanButton.post {
            scanButton.text = "▶  SCAN"
            scanButton.isEnabled = true
        }

        if (combined == null) {
            autoStopPending = false
            captureRequested = false
            autoScanLogPending = false
            autoGrainSavePending = false
            runOnUiThread {
                recordPrecisionScanFailure("測定結果が揃いませんでした。もう一度スキャンしてください")
            }
            return
        }
'''

new_block='''        val precisionMinWindows = 5
        val precisionMaxWindows = 8
        if (consensusWindowIndex < precisionMinWindows) {
            consensusWindowStartedMs = now
            runOnUiThread {
                if (scanning) {
                    status.text = "複数回測定中… " +
                        consensusWindowIndex + "/" + precisionMinWindows
                }
            }
            return
        }

        val aggregateSurface = if (precisionLogPoints.size >= 500) {
            PrecisionSurfaceBuilder.build(precisionLogPoints, marks.first, marks.second)
        } else null
        precisionSurface = aggregateSurface
        val aggregateReport = aggregateSurface?.let {
            PrecisionSlopeAnalyzer.analyze(it, marks.first, marks.second)
        }
        val aggregateDiagnostic = if (aggregateSurface == null) {
            "AGG@" + consensusWindowIndex + ": points=" + precisionLogPoints.size + " surface=null"
        } else if (aggregateReport == null) {
            "AGG@" + consensusWindowIndex + ": rejected points=" + aggregateSurface.sourcePointCount +
                " frames=" + aggregateSurface.uniqueFrames +
                " ground=" + aggregateSurface.groundCellCount +
                " surface=[" + PrecisionSurfaceBuilder.lastDiagnostic +
                "] analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"
        } else {
            "AGG@" + consensusWindowIndex + ": OK points=" + aggregateSurface.sourcePointCount +
                " frames=" + aggregateSurface.uniqueFrames +
                " ground=" + aggregateSurface.groundCellCount +
                " long=" + String.format("%.2f", aggregateReport.overallLongitudinalPercent) +
                " cross=" + String.format("%.2f", aggregateReport.overallCrossPercent)
        }
        precisionLastDiagnostic =
            (precisionWindowDiagnostics + aggregateDiagnostic).joinToString(" | ")

        // Prefer the aggregate surface. Per-window consensus is the fallback.
        // If neither is valid after the normal five windows, gather more Depth
        // automatically instead of failing the whole scan immediately.
        val combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined

        if (combined == null && consensusWindowIndex < precisionMaxWindows) {
            consensusWindowStartedMs = now
            runOnUiThread {
                if (scanning) {
                    status.text = "追加測定中… " +
                        consensusWindowIndex + "/" + precisionMaxWindows +
                        "（端末をゆっくり動かしてください）"
                }
            }
            return
        }

        scanning = false
        scanButton.post {
            scanButton.text = "▶  SCAN"
            scanButton.isEnabled = true
        }

        if (combined == null) {
            autoStopPending = false
            captureRequested = false
            autoScanLogPending = false
            autoGrainSavePending = false
            runOnUiThread {
                recordPrecisionScanFailure("追加測定しても結果が安定しませんでした。もう一度スキャンしてください")
            }
            return
        }
'''
once(old_block,new_block,"adaptive extra windows")

# Version only. Measurement thresholds, slope caps and ground gates are untouched.
if "Precision 6.8" not in s:
    raise SystemExit("v6.9 source version target missing")
s=s.replace("Precision 6.8","Precision 6.9")

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.8"') != 1 or g.count('versionCode = 680') != 1:
    raise SystemExit("v6.9 Gradle version target missing")
g=g.replace('versionName = "6.8"','versionName = "6.9"',1)
g=g.replace('versionCode = 680','versionCode = 690',1)

assert "precisionCollector.size() >= 250 && precisionCollector.uniqueFrames() >= 3" in s
assert "precisionWindowElapsedMs < 1200L" in s
assert "val precisionMinWindows = 5" in s
assert "val precisionMaxWindows = 8" in s
assert '"追加測定中… "' in s
# Accuracy boundary guards: do not loosen these in the acquisition fix.
analyzer=Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt").read_text(encoding="utf-8")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in analyzer
assert "MAX_LOCAL_RMSE_METERS = 0.040" in analyzer
assert "LOCAL_FIT_RADIUS_METERS = 0.32f" in analyzer

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.9 adaptive scan acquisition")
# Trigger Precision v6.9 build
