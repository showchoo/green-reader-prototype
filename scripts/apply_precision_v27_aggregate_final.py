from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

old='''        val combined = SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined
'''
new='''        val aggregateSurface = if (precisionLogPoints.size >= 500) {
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
'''
if old not in s:
    raise SystemExit("v3.9 target missing: final consensus")
s=s.replace(old,new,1)

p.write_text(s,encoding="utf-8")
print("Applied Precision v3.9 aggregate five-window final analysis")
