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

s = s.replace('appVersion = "Precision 2.2"', 'appVersion = "Precision 4.5"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 220', 'versionCode = 450')
b = b.replace('versionName = "2.2"', 'versionName = "4.5"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v2.3 detailed window diagnostics")


# Keep analyzer diagnostics deterministic after earlier Precision patches rewrite sources.
analyzer = Path("app/src/main/java/jp/example/greenreader/precision/PrecisionSlopeAnalyzer.kt")
analyzer.write_text("package jp.example.greenreader.precision\n\nimport jp.example.greenreader.analysis.SlopeReport\nimport jp.example.greenreader.analysis.SlopeSegment\nimport jp.example.greenreader.analysis.Vec3\nimport kotlin.math.abs\nimport kotlin.math.sqrt\n\nobject PrecisionSlopeAnalyzer {\n    private const val MAX_USABLE_SLOPE_PERCENT = 12f\n    private const val MAX_LOCAL_RMSE_METERS = 0.040\n    private const val LOCAL_FIT_RADIUS_METERS = 0.45f\n\n    @Volatile var lastDiagnostic: String = \"\"\n        private set\n\n    fun analyze(\n        surface: PrecisionSurfaceModel,\n        ball: Vec3,\n        cup: Vec3,\n        segmentCount: Int = 8\n    ): SlopeReport? {\n        val dx = cup.x - ball.x\n        val dz = cup.z - ball.z\n        val distance = sqrt(dx * dx + dz * dz)\n\n        if (distance < 0.4f || surface.groundCellCount < 25 || surface.uniqueFrames < 3) {\n            lastDiagnostic = \"precheck distance=\" + String.format(\"%.2f\", distance) +\n                \" ground=\" + surface.groundCellCount +\n                \" frames=\" + surface.uniqueFrames\n            return null\n        }\n\n        val fx = dx / distance\n        val fz = dz / distance\n        val rx = -fz\n        val rz = fx\n\n        val segments = ArrayList<SlopeSegment>()\n        val segmentDiagnostics = ArrayList<String>(segmentCount)\n        var fitMissing = 0\n        var rmseRejected = 0\n        var slopeRejected = 0\n        var maxSeenSlope = 0f\n        var maxSeenRmse = 0.0\n\n        fun nearbySamples(cx: Float, cz: Float): Int {\n            val r2 = LOCAL_FIT_RADIUS_METERS * LOCAL_FIT_RADIUS_METERS\n            return surface.cells.count { c ->\n                val sx = c.x - cx\n                val sz = c.z - cz\n                sx * sx + sz * sz <= r2\n            }\n        }\n\n        for (i in 0 until segmentCount) {\n            val t = (i + 0.5f) / segmentCount\n            val cx = ball.x + dx * t\n            val cz = ball.z + dz * t\n            val nearby = nearbySamples(cx, cz)\n            val alongMin = surface.cells.minOfOrNull { (it.x - ball.x) * fx + (it.z - ball.z) * fz }\n            val alongMax = surface.cells.maxOfOrNull { (it.x - ball.x) * fx + (it.z - ball.z) * fz }\n            val fit = PrecisionLocalQuadraticFitter.fit(\n                surface.cells, cx, cz, fx, fz, rx, rz,\n                radiusMeters = LOCAL_FIT_RADIUS_METERS\n            )\n            if (fit == null) {\n                fitMissing++\n                segmentDiagnostics += \"S${i + 1} fit=null n=$nearby c=\" + String.format(\"%.2f\", distance * t) + \" span=\" + String.format(\"%.2f..%.2f\", alongMin ?: Float.NaN, alongMax ?: Float.NaN)\n                continue\n            }\n\n            if (fit.rmseMeters > maxSeenRmse) maxSeenRmse = fit.rmseMeters\n            val forward = (fit.dHdForward * 100.0).toFloat()\n            val right = (fit.dHdRight * 100.0).toFloat()\n            val total = sqrt(forward * forward + right * right)\n            if (total.isFinite() && total > maxSeenSlope) maxSeenSlope = total\n\n            val values =\n                \"n=${fit.samples} rmse=\" + String.format(\"%.3f\", fit.rmseMeters) +\n                \" f=\" + String.format(\"%.1f\", forward) + \"%\" +\n                \" r=\" + String.format(\"%.1f\", right) + \"%\" +\n                \" total=\" + String.format(\"%.1f\", total) + \"%\"\n\n            if (fit.rmseMeters > MAX_LOCAL_RMSE_METERS) {\n                rmseRejected++\n                segmentDiagnostics += \"S${i + 1} RMSE>4cm $values\"\n                continue\n            }\n\n            if (!forward.isFinite() || !right.isFinite() || !total.isFinite()) {\n                slopeRejected++\n                segmentDiagnostics += \"S${i + 1} nonfinite $values\"\n                continue\n            }\n            if (total > MAX_USABLE_SLOPE_PERCENT) {\n                slopeRejected++\n                segmentDiagnostics += \"S${i + 1} slope>12% $values\"\n                continue\n            }\n\n            segmentDiagnostics += \"S${i + 1} OK $values\"\n            val start = distance * i / segmentCount\n            val end = distance * (i + 1) / segmentCount\n            val elevation = ball.y + (cup.y - ball.y) * t\n            segments += SlopeSegment(\n                startMeters = start,\n                endMeters = end,\n                longitudinalPercent = forward,\n                crossPercent = right,\n                elevationMeters = elevation,\n                sampleCount = fit.samples\n            )\n        }\n\n        val prefix =\n            \"distance=\" + String.format(\"%.2f\", distance) +\n            \" ground=\" + surface.groundCellCount +\n            \" frames=\" + surface.uniqueFrames +\n            \" valid=\" + segments.size + \"/\" + segmentCount +\n            \" fitMissing=\" + fitMissing +\n            \" rmseRejected=\" + rmseRejected +\n            \" slopeRejected=\" + slopeRejected\n\n        if (segments.size < 4) {\n            lastDiagnostic = prefix + \" final=validSegments<4 | \" +\n                segmentDiagnostics.joinToString(\" | \")\n            return null\n        }\n\n        fun median(values: List<Float>): Float {\n            val s = values.sorted()\n            val m = s.size / 2\n            return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) * 0.5f\n        }\n\n        val longitudinal = median(segments.map { it.longitudinalPercent })\n        val cross = median(segments.map { it.crossPercent })\n        if (abs(longitudinal) > MAX_USABLE_SLOPE_PERCENT ||\n            abs(cross) > MAX_USABLE_SLOPE_PERCENT) {\n            lastDiagnostic = prefix +\n                \" final=medianOverflow long=\" + String.format(\"%.2f\", longitudinal) +\n                \" cross=\" + String.format(\"%.2f\", cross) + \" | \" +\n                segmentDiagnostics.joinToString(\" | \")\n            return null\n        }\n\n        lastDiagnostic = prefix +\n            \" final=OK long=\" + String.format(\"%.2f\", longitudinal) +\n            \" cross=\" + String.format(\"%.2f\", cross) + \" | \" +\n            segmentDiagnostics.joinToString(\" | \")\n\n        return SlopeReport(\n            distanceMeters = distance,\n            segments = segments,\n            overallLongitudinalPercent = longitudinal,\n            overallCrossPercent = cross,\n            pointCount = surface.sourcePointCount\n        )\n    }\n}\n", encoding="utf-8")
print("Applied Precision segment-level analyzer diagnostics")
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
