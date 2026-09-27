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
                "W${consensusWindowIndex + 1}: 地面抽出不足 points=${precisionWindowSurface.sourcePointCount} frames=${precisionWindowSurface.uniqueFrames} candidate=${precisionWindowSurface.candidateCellCount} ground=${precisionWindowSurface.groundCellCount} rejected=${precisionWindowSurface.rejectedCellCount}"
            precisionCandidate == null ->
                "W${consensusWindowIndex + 1}: 傾斜解析却下 points=${precisionWindowSurface.sourcePointCount} frames=${precisionWindowSurface.uniqueFrames} candidate=${precisionWindowSurface.candidateCellCount} ground=${precisionWindowSurface.groundCellCount} rejected=${precisionWindowSurface.rejectedCellCount}"
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

s = s.replace('appVersion = "Precision 2.2"', 'appVersion = "Precision 2.6"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 220', 'versionCode = 260')
b = b.replace('versionName = "2.2"', 'versionName = "2.6"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v2.3 detailed window diagnostics")
