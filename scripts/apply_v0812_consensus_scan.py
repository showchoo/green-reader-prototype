from pathlib import Path

main_path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.12 pattern not found ({label}):\n{old[:1600]}")
    s = s.replace(old, new, 1)


# Keep five independent short measurements. A single bad Depth window is allowed;
# final direction is chosen by 3-of-5 agreement and magnitudes by medians.
replace_once(
    "    private var scanStartMs = 0L\n",
    """    private var scanStartMs = 0L
    private val consensusReports = ArrayList<SlopeReport>(5)
    private val consensusLogPoints = ArrayList<Vec3>(60000)
    private var consensusWindowStartedMs = 0L
    private var consensusWindowIndex = 0
    private var consensusReport: SlopeReport? = null
""",
    "consensus state fields",
)

# Replace scan start/stop behavior. There is no manual early-stop result anymore:
# one press performs all five windows automatically, keeping the field workflow simple.
start = s.find("    private fun toggleScan() {")
end = s.find("    private fun requestCaptureAndAnalyze(", start)
if start < 0 or end < 0:
    raise SystemExit("v0.8.12 toggleScan boundaries not found")
new_toggle = '''    private fun toggleScan() {
        if (scanning) return
        if (ball == null || cup == null) {
            status.text = if (ball == null) "ボールをタップしてください" else "カップをタップしてください"
            return
        }
        if (ballAnchor?.trackingState != TrackingState.TRACKING ||
            cupAnchor?.trackingState != TrackingState.TRACKING) {
            status.text = "位置追跡を準備中です。端末を少し動かしてから再試行してください"
            return
        }

        pendingMark = null
        showCamera()
        collector.clear()
        consensusReports.clear()
        consensusLogPoints.clear()
        consensusWindowIndex = 0
        consensusReport = null
        val now = SystemClock.elapsedRealtime()
        consensusWindowStartedMs = now
        scanStartMs = now
        autoStopPending = false
        captureRequested = false
        autoGrainSavePending = true
        autoScanLogPending = true
        scanning = true
        restartRenderLoop()
        scanButton.text = "測定中…"
        scanButton.isEnabled = false
        status.text = "複数回測定中… 端末をゆっくり動かしてください"
    }

'''
s = s[:start] + new_toggle + s[end:]

# Replace single-scan auto-finish with five independent 650 ms windows. Each window
# is analyzed before clearing the collector, so one reversed/noisy acquisition only
# contributes one vote rather than contaminating all subsequent frames.
start = s.find("    private fun maybeAutoFinishScan() {")
end = s.find("    private fun captureGlFrame(", start)
if start < 0 or end < 0:
    raise SystemExit("v0.8.12 maybeAutoFinishScan boundaries not found")
new_finish = '''    private fun maybeAutoFinishScan() {
        if (!scanning || autoStopPending) return
        val now = SystemClock.elapsedRealtime()
        val marks = currentAnalysisMarks()
        if (marks == null) {
            if (now - scanStartMs > 8000L) {
                scanning = false
                autoScanLogPending = false
                autoGrainSavePending = false
                runOnUiThread {
                    scanButton.text = "スキャン開始"
                    scanButton.isEnabled = true
                    status.text = "位置追跡が安定しませんでした。もう一度スキャンしてください"
                }
            }
            return
        }

        if (now - consensusWindowStartedMs < 650L) return

        val points = collector.snapshot()
        val room = (60000 - consensusLogPoints.size).coerceAtLeast(0)
        if (room > 0 && points.isNotEmpty()) {
            val toKeep = if (points.size <= room) points else points.takeLast(room)
            consensusLogPoints.addAll(toKeep)
        }

        val candidate = SlopeAnalyzer.analyze(points, marks.first, marks.second)
        if (candidate != null && candidate.pointCount >= 80) {
            consensusReports += candidate
        }

        collector.clear()
        consensusWindowIndex += 1

        if (consensusWindowIndex < 5) {
            consensusWindowStartedMs = now
            runOnUiThread {
                if (scanning) status.text = "複数回測定中… 端末をゆっくり動かしてください"
            }
            return
        }

        val combined = SlopeConsensus.combine(consensusReports)
        consensusReport = combined
        scanning = false
        scanButton.post {
            scanButton.text = "スキャン開始"
            scanButton.isEnabled = true
        }

        if (combined == null) {
            autoStopPending = false
            captureRequested = false
            autoScanLogPending = false
            autoGrainSavePending = false
            runOnUiThread {
                status.text = "測定結果が揃いませんでした。もう一度スキャンしてください"
            }
            return
        }

        autoStopPending = true
        captureRequested = true
        runOnUiThread {
            status.text = "複数回の測定結果を照合しました。解析中…"
        }
    }

'''
s = s[:start] + new_finish + s[end:]

# Final analysis must consume the consensus result, never re-run a single final
# collector window and accidentally throw away the majority decision.
old_report = '''        val b = marks.first
        val c = marks.second
        val report = SlopeAnalyzer.analyze(collector.snapshot(), b, c)
        if (report == null) {
            if (updateStatus) status.text = "データ不足です。もう一度3秒スキャンしてください"
            return
        }
'''
new_report = '''        val b = marks.first
        val c = marks.second
        val report = consensusReport
        if (report == null) {
            if (updateStatus) status.text = "測定結果が安定しませんでした。もう一度スキャンしてください"
            return
        }
'''
replace_once(old_report, new_report, "analyze consensus result")

# Preserve a useful point cloud in field logs even though the active collector is
# cleared between measurement windows.
replace_once(
    "            val pointsForLog = collector.snapshot()\n",
    "            val pointsForLog = if (consensusLogPoints.isNotEmpty()) consensusLogPoints.toList() else collector.snapshot()\n",
    "log points from all windows",
)

# Reset must clear every consensus state and restore the scan button.
reset_start = s.find("    private fun resetAll() {")
reset_end = s.find("    private fun showMap()", reset_start)
if reset_start < 0 or reset_end < 0:
    raise SystemExit("v0.8.12 resetAll boundaries not found")
reset = s[reset_start:reset_end]
reset = reset.replace(
    '        scanButton.text = "スキャン開始"\n',
    '        scanButton.text = "スキャン開始"\n        scanButton.isEnabled = true\n',
    1,
)
reset = reset.replace(
    '        collector.clear()\n',
    '''        consensusReports.clear()
        consensusLogPoints.clear()
        consensusWindowIndex = 0
        consensusWindowStartedMs = 0L
        consensusReport = null
        collector.clear()
''',
    1,
)
s = s[:reset_start] + reset + s[reset_end:]

# Logs identify the field build that produced the consensus result.
s = s.replace('appVersion = "0.8.0"', 'appVersion = "0.8.12"')

main_path.write_text(s, encoding="utf-8")

# On effectively flat segments the sign is noise; do not draw a meaningless cyan
# direction arrow. Real direction changes still require the 3-of-5 segment vote.
overlay_path = Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt")
overlay = overlay_path.read_text(encoding="utf-8")
needle = """        r.segments.forEachIndexed { i, seg ->
            val t = (i + 0.5f) / r.segments.size
"""
replacement = """        r.segments.forEachIndexed { i, seg ->
            if (abs(seg.crossPercent) < 0.15f) return@forEachIndexed
            val t = (i + 0.5f) / r.segments.size
"""
if needle not in overlay:
    raise SystemExit("v0.8.12 overlay segment loop not found")
overlay = overlay.replace(needle, replacement, 1)
overlay_path.write_text(overlay, encoding="utf-8")

print("Applied v0.8.12 five-window consensus scan")
