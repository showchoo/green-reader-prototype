from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"v2.3 target missing: {label}")
    s = s.replace(old, new, 1)

once(
    '    private var precisionLastDiagnostic: String = ""\n',
    '    private var precisionLastDiagnostic: String = ""\n'
    '    private val precisionWindowDiagnostics = ArrayList<String>(8)\n',
    'diagnostic list field'
)

once(
    '        precisionLogPoints.clear()\n        precisionSurface = null\n',
    '        precisionLogPoints.clear()\n        precisionSurface = null\n'
    '        precisionWindowDiagnostics.clear()\n'
    '        precisionLastDiagnostic = ""\n',
    'scan reset diagnostics'
)

needle = '        consensusReport = null\n        precisionLogPoints.clear()\n        precisionSurface = null\n        precisionCollector.clear()\n'
if needle in s:
    s = s.replace(
        needle,
        '        consensusReport = null\n'
        '        precisionLogPoints.clear()\n'
        '        precisionSurface = null\n'
        '        precisionWindowDiagnostics.clear()\n'
        '        precisionLastDiagnostic = ""\n'
        '        precisionCollector.clear()\n',
        1
    )

old = '''        val precisionCandidate = if (precisionPoints.size >= 250) {
            val surface = PrecisionSurfaceBuilder.build(precisionPoints)
            PrecisionSlopeAnalyzer.analyze(surface, marks.first, marks.second)
        } else null
        val candidate = precisionCandidate
'''
new = '''        val precisionWindowSurface = if (precisionPoints.size >= 250) {
            PrecisionSurfaceBuilder.build(precisionPoints)
        } else null
        val precisionCandidate = precisionWindowSurface?.let {
            PrecisionSlopeAnalyzer.analyze(it, marks.first, marks.second)
        }

        val windowDiagnostic = when {
            precisionPoints.size < 250 ->
                "W${consensusWindowIndex + 1}: RawDepth点不足 " + precisionCollector.diagnosticSummary()
            precisionWindowSurface == null ->
                "W${consensusWindowIndex + 1}: Surface生成失敗 points=${precisionPoints.size}"
            precisionWindowSurface.groundCellCount < 25 ->
                "W${consensusWindowIndex + 1}: 地面抽出不足 points=${precisionWindowSurface.sourcePointCount} frames=${precisionWindowSurface.uniqueFrames} candidate=${precisionWindowSurface.candidateCellCount} ground=${precisionWindowSurface.groundCellCount} rejected=${precisionWindowSurface.rejectedCellCount} surface=[" + PrecisionSurfaceBuilder.lastDiagnostic + "]"
            precisionCandidate == null ->
                "W${consensusWindowIndex + 1}: 傾斜解析却下 points=${precisionWindowSurface.sourcePointCount} frames=${precisionWindowSurface.uniqueFrames} candidate=${precisionWindowSurface.candidateCellCount} ground=${precisionWindowSurface.groundCellCount} rejected=${precisionWindowSurface.rejectedCellCount} analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"
            else ->
                "W${consensusWindowIndex + 1}: OK points=${precisionWindowSurface.sourcePointCount} frames=${precisionWindowSurface.uniqueFrames} ground=${precisionWindowSurface.groundCellCount} long=" + String.format("%.2f", precisionCandidate.overallLongitudinalPercent) + " cross=" + String.format("%.2f", precisionCandidate.overallCrossPercent)
        }
        precisionWindowDiagnostics += windowDiagnostic
        precisionLastDiagnostic = precisionWindowDiagnostics.joinToString(" | ")

        val candidate = precisionCandidate
'''
once(old, new, 'window diagnostics')

s = s.replace(
    'val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic',
    'val detail = if (precisionLastDiagnostic.isBlank()) "診断未生成: RawDepth収集前または予期しない経路で終了" else precisionLastDiagnostic',
    1
)

s = s.replace('appVersion = "Precision 2.2"', 'appVersion = "Precision 5.4"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 220', 'versionCode = 540')
b = b.replace('versionName = "2.2"', 'versionName = "5.4"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v2.3 detailed window diagnostics")


# Do not rewrite PrecisionSlopeAnalyzer.kt here.
# The checked-in analyzer is the canonical implementation; overwriting it from this
# diagnostics patch previously erased later global-plane regularization.
# Rebuild marker for Precision v2.8
# Trigger Precision v2.9 build
# Trigger Precision v3.0 build
# Trigger Precision v3.1 build
# Trigger Precision v3.2 build
# Trigger Precision v3.3 build
# Trigger Precision v3.4 build
# Trigger Precision v3.5 build
# Trigger Precision v3.6 fixed-signing build
# Trigger Precision v3.7 build
# Trigger Precision v3.8 build
# Retrigger Precision v3.8 build after patch-order fix
# Trigger Precision v4.0 build
# Trigger Precision v4.1 build
# Trigger Precision v4.5 build
# Trigger Precision v4.6 build
# Trigger Precision v4.7 build
# Trigger Precision v4.8 build
# Trigger Precision v4.9 build
# Trigger Precision v5.0 build
# Trigger Precision v5.1 build
# Trigger Precision v5.2 build
# Trigger Precision v5.3 build
# Trigger Precision v5.4 build
