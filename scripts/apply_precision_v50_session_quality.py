"""v7.0: session/putt/scan identity, repeatability diagnostics and scan confidence."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"v7.0 {label}: expected 1 target, got {count}")
    s = s.replace(old, new, 1)

def replace_function(name: str, replacement: str) -> None:
    global s
    start = s.index(f"    private fun {name}(")
    end = s.find("\n    private fun ", start + 20)
    if end < 0:
        raise SystemExit(f"v7.0 next function not found after {name}")
    s = s[:start] + replacement.rstrip() + "\n" + s[end:]

# ---------------------------------------------------------------------------
# 1. Persistent field-test identity and quality state.
# ---------------------------------------------------------------------------
once(
'''    private var latestCameraQuaternion = floatArrayOf(0f, 0f, 0f, 1f)
''',
'''    private var latestCameraQuaternion = floatArrayOf(0f, 0f, 0f, 1f)

    // One app launch = one field-test session. Repeated scans with the same
    // Ball/Cup pair stay under one Putt ID and receive consecutive Scan IDs.
    private val precisionFieldSessionId: String =
        java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.US).format(java.util.Date()) +
            "_" + java.util.UUID.randomUUID().toString().take(8)
    private var precisionPuttId = 1
    private var precisionScanIndex = 0
    private var precisionCurrentRecord: ScanFieldRecorder.RecordIdentity? = null
    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null
    private val precisionCollectorWindowSnapshots =
        ArrayList<jp.example.greenreader.precision.PrecisionDepthCollector.DiagnosticsSnapshot>(8)
    private val precisionTrackingMonitor =
        jp.example.greenreader.precision.PrecisionTrackingMonitor()
    private lateinit var precisionRecordLabel: TextView
''',
"identity fields"
)

# ---------------------------------------------------------------------------
# 2. Put the current record identity/quality into the collapsible field menu.
# ---------------------------------------------------------------------------
once(
'''        panel.addView(expandedMenu)
''',
'''        precisionRecordLabel = TextView(this).apply {
            setTextColor(Color.rgb(171, 255, 226))
            textSize = 10.5f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
            setPadding(dp(7), dp(8), dp(7), dp(5))
        }
        expandedMenu.addView(precisionRecordLabel)

        val row6 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row6.addView(
            button("次のパット") { beginNextPrecisionPutt() },
            LinearLayout.LayoutParams(0, dp(42), 1f)
        )
        expandedMenu.addView(row6)
        updatePrecisionRecordLabel()

        panel.addView(expandedMenu)
''',
"record controls"
)

# ---------------------------------------------------------------------------
# 3. Freeze one identity at scan start. Failures consume a Scan number too.
# ---------------------------------------------------------------------------
once(
'''        pendingMark = null
        showCamera()
        collector.clear()
''',
'''        pendingMark = null
        showCamera()

        precisionScanIndex += 1
        val recordStartedAt = System.currentTimeMillis()
        precisionCurrentRecord = ScanFieldRecorder.RecordIdentity(
            sessionId = precisionFieldSessionId,
            puttId = precisionPuttId,
            scanIndex = precisionScanIndex,
            scanStartedAtEpochMs = recordStartedAt,
            scanFinishedAtEpochMs = recordStartedAt
        )
        precisionCurrentQuality = null
        precisionCollectorWindowSnapshots.clear()
        precisionTrackingMonitor.reset()
        updatePrecisionRecordLabel()

        collector.clear()
''',
"scan identity start"
)

# ---------------------------------------------------------------------------
# 4. Track camera health only while a measurement is active.
# ---------------------------------------------------------------------------
once(
'''            latestCameraQuaternion = FloatArray(4).also { latestPose.getRotationQuaternion(it, 0) }
''',
'''            latestCameraQuaternion = FloatArray(4).also { latestPose.getRotationQuaternion(it, 0) }
            if (scanning) {
                precisionTrackingMonitor.observe(
                    if (f.camera.trackingState == TrackingState.TRACKING) latestPose else null,
                    f.camera.trackingState,
                    f.timestamp
                )
            }
''',
"tracking monitor"
)

# ---------------------------------------------------------------------------
# 5. Keep one immutable Depth diagnostic snapshot for every W1..W8 window.
#    The active collector is cleared between windows, so this must happen first.
# ---------------------------------------------------------------------------
once(
'''        collector.clear()
        precisionCollector.clear()
        consensusWindowIndex += 1
''',
'''        precisionCollectorWindowSnapshots += precisionCollector.diagnosticSnapshot()
        collector.clear()
        precisionCollector.clear()
        consensusWindowIndex += 1
''',
"window diagnostic snapshot"
)

# ---------------------------------------------------------------------------
# 6. Evaluate quality from the reconstructed aggregate surface, independent
#    window repeatability and AR tracking stability.
# ---------------------------------------------------------------------------
once(
'''        val combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined

        if (combined == null && consensusWindowIndex < precisionMaxWindows) {
''',
'''        val combined = aggregateReport ?: SlopeConsensus.combine(consensusReports, minAgree = 4)
        consensusReport = combined

        precisionCurrentQuality =
            jp.example.greenreader.precision.PrecisionQualityEstimator.evaluate(
                surface = aggregateSurface,
                report = combined,
                windowReports = consensusReports,
                collectorWindows = precisionCollectorWindowSnapshots,
                tracking = precisionTrackingMonitor.snapshot(),
                ball = marks.first,
                cup = marks.second
            )
        precisionCurrentQuality?.let { quality ->
            precisionLastDiagnostic += " | QUALITY: " + quality.summary()
            updatePrecisionRecordLabel()
        }

        if (combined == null && consensusWindowIndex < precisionMaxWindows) {
''',
"quality evaluation"
)

# ---------------------------------------------------------------------------
# 7. Group failed field packages under Session/Putt/Scan and keep quality.
# ---------------------------------------------------------------------------
replace_function("recordPrecisionScanFailure", r'''    private fun recordPrecisionScanFailure(message: String) {
        val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
        val full = message + "\n\n" + detail
        val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
        prefs.edit()
            .putString("last_failure", full)
            .putLong("last_failure_time", System.currentTimeMillis())
            .apply()

        if (!precisionFailureRecordSaved) {
            precisionFailureRecordSaved = true
            val precisionPointsForLog =
                if (precisionLogPoints.isNotEmpty()) precisionLogPoints.toList()
                else precisionCollector.snapshot()
            val markerDiagnostic = prefs.getString("last_marker", "") ?: ""
            val collectorDiagnostic =
                precisionCollector.diagnosticSummary() +
                    " quality=" + (precisionCurrentQuality?.summary() ?: "-")
            val ballForLog = ball
            val cupForLog = cup
            val meta = ScanFieldRecorder.CaptureMeta(
                appVersion = "Precision 7.0",
                trackingState = trackingStateText,
                viewportWidth = viewportW,
                viewportHeight = viewportH,
                cameraTranslation = latestCameraTranslation.copyOf(),
                cameraQuaternion = latestCameraQuaternion.copyOf(),
                ballScreenX = null,
                ballScreenY = null,
                cupScreenX = null,
                cupScreenY = null,
                arCoreDepthSupported = depthSupported
            )
            val identity = finalPrecisionRecordIdentity()
            val quality = precisionCurrentQuality
            Thread {
                try {
                    if (identity != null) {
                        ScanFieldRecorder.saveFailureGrouped(
                            this,
                            precisionPointsForLog,
                            ballForLog,
                            cupForLog,
                            message,
                            detail,
                            markerDiagnostic,
                            collectorDiagnostic,
                            meta,
                            identity,
                            quality
                        )
                    } else {
                        ScanFieldRecorder.saveFailure(
                            this,
                            precisionPointsForLog,
                            ballForLog,
                            cupForLog,
                            message,
                            detail,
                            markerDiagnostic,
                            collectorDiagnostic,
                            meta
                        )
                    }
                } catch (_: Throwable) {
                    // Field logging must never block another measurement.
                }
            }.start()
        }

        val advice = precisionCurrentQuality?.guidance?.firstOrNull()
        status.text = if (advice.isNullOrBlank()) {
            message + "（自動保存済み）"
        } else {
            message + "\n" + advice + "（自動保存済み）"
        }
        Toast.makeText(this, "再スキャンできます", Toast.LENGTH_SHORT).show()
        updatePrecisionRecordLabel()
    }
''')

# ---------------------------------------------------------------------------
# 8. Group successful field packages too. Keep the legacy fallback only if an
#    identity is unexpectedly unavailable.
# ---------------------------------------------------------------------------
old_success = '''                    val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
                    ScanFieldRecorder.save(
                        this,
                        bitmapForLog,
                        pointsForLog,
                        b,
                        c,
                        report,
                        adv,
                        grainForLog,
                        meta,
                        precisionPoints = precisionLogPoints.toList(),
                        precisionDiagnostic = precisionLastDiagnostic,
                        markerDiagnostic = prefs.getString("last_marker", "") ?: "",
                        collectorDiagnostic = precisionCollector.diagnosticSummary()
                    )
'''
new_success = '''                    val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
                    val identity = finalPrecisionRecordIdentity()
                    if (identity != null) {
                        ScanFieldRecorder.saveGrouped(
                            this,
                            bitmapForLog,
                            pointsForLog,
                            b,
                            c,
                            report,
                            adv,
                            grainForLog,
                            meta.copy(arCoreDepthSupported = depthSupported),
                            precisionPoints = precisionLogPoints.toList(),
                            precisionDiagnostic = precisionLastDiagnostic,
                            markerDiagnostic = prefs.getString("last_marker", "") ?: "",
                            collectorDiagnostic =
                                precisionCollector.diagnosticSummary() +
                                    " quality=" + (precisionCurrentQuality?.summary() ?: "-"),
                            identity = identity,
                            quality = precisionCurrentQuality
                        )
                    } else {
                        ScanFieldRecorder.save(
                            this,
                            bitmapForLog,
                            pointsForLog,
                            b,
                            c,
                            report,
                            adv,
                            grainForLog,
                            meta,
                            precisionPoints = precisionLogPoints.toList(),
                            precisionDiagnostic = precisionLastDiagnostic,
                            markerDiagnostic = prefs.getString("last_marker", "") ?: "",
                            collectorDiagnostic = precisionCollector.diagnosticSummary()
                        )
                    }
'''
once(old_success, new_success, "grouped success save")

# ---------------------------------------------------------------------------
# 9. A new Ball after a completed/attempted putt automatically starts a new Putt
#    unless the user already used the explicit Next Putt action.
# ---------------------------------------------------------------------------
once(
'''        if (mode == 1) {
            ballAnchor?.detach()
''',
'''        if (mode == 1) {
            if (cup != null || precisionScanIndex > 0) {
                precisionPuttId += 1
                precisionScanIndex = 0
                precisionCurrentRecord = null
                precisionCurrentQuality = null
            }
            ballAnchor?.detach()
''',
"automatic new putt"
)

# ---------------------------------------------------------------------------
# 10. Helpers: final timestamp, manual Next Putt, and compact status label.
# ---------------------------------------------------------------------------
marker = "    private fun showPrecisionFailureDialog(message: String) {"
idx = s.index(marker)
helpers = r'''    private fun finalPrecisionRecordIdentity(): ScanFieldRecorder.RecordIdentity? {
        val current = precisionCurrentRecord ?: return null
        return current.copy(scanFinishedAtEpochMs = System.currentTimeMillis())
    }

    private fun beginNextPrecisionPutt() {
        if (scanning) {
            Toast.makeText(this, "測定終了後に次のパットへ進んでください", Toast.LENGTH_SHORT).show()
            return
        }
        precisionPuttId += 1
        precisionScanIndex = 0
        precisionCurrentRecord = null
        precisionCurrentQuality = null
        precisionCollectorWindowSnapshots.clear()
        precisionTrackingMonitor.reset()
        precisionFailureRecordSaved = false

        pendingMark = null
        ballAnchor?.detach()
        cupAnchor?.detach()
        ballAnchor = null
        cupAnchor = null
        ball = null
        cup = null
        markMode = 1

        collector.clear()
        precisionCollector.clear()
        consensusReports.clear()
        consensusLogPoints.clear()
        precisionLogPoints.clear()
        precisionSurface = null
        consensusReport = null
        overlayView.clear()
        mapView.report = null
        showCamera()
        updatePrecisionRecordLabel()
        status.text = "Putt " + String.format("%03d", precisionPuttId) +
            "：ボールをタップしてください"
    }

    private fun updatePrecisionRecordLabel() {
        if (!::precisionRecordLabel.isInitialized) return
        val shortSession = precisionFieldSessionId.takeLast(8)
        val q = precisionCurrentQuality
        val qualityText = if (q == null) {
            "QUALITY --"
        } else {
            "QUALITY " + q.score + " " + q.tier +
                " ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%"
        }
        precisionRecordLabel.text =
            "SESSION " + shortSession +
                "  /  PUTT " + String.format("%03d", precisionPuttId) +
                "  /  SCAN " + String.format("%02d", precisionScanIndex) +
                "\n" + qualityText
    }

'''
s = s[:idx] + helpers + s[idx:]

# Reset should not destroy the field session, but must not leave stale quality.
once(
'''        precisionSurface = null
        precisionWindowDiagnostics.clear()
        precisionLastDiagnostic = ""
        precisionCollector.clear()
''',
'''        precisionSurface = null
        precisionWindowDiagnostics.clear()
        precisionLastDiagnostic = ""
        precisionCurrentRecord = null
        precisionCurrentQuality = null
        precisionCollectorWindowSnapshots.clear()
        precisionTrackingMonitor.reset()
        precisionCollector.clear()
''',
"reset quality state"
)

# v7.0 product/development marker.
if 'Precision 6.9' not in s:
    raise SystemExit("v7.0 source version target missing")
s = s.replace('Precision 6.9', 'Precision 7.0')

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.9"') != 1 or g.count('versionCode = 690') != 1:
    raise SystemExit("v7.0 Gradle version target missing")
g = g.replace('versionName = "6.9"', 'versionName = "7.0"', 1)
g = g.replace('versionCode = 690', 'versionCode = 700', 1)

# Safety/feature assertions.
assert "saveGrouped(" in s
assert "saveFailureGrouped(" in s
assert "precisionCollectorWindowSnapshots += precisionCollector.diagnosticSnapshot()" in s
assert "PrecisionQualityEstimator.evaluate(" in s
assert "precisionTrackingMonitor.observe(" in s
assert 'button("次のパット")' in s
assert "precisionScanIndex += 1" in s
assert "appVersion = \"Precision 7.0\"" in s

main.write_text(s, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v7.0 session grouping + scan quality")
