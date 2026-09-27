from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v1.9 target missing ({label}): {old[:500]}")
    s = s.replace(old, new, 1)

# Fields.
replace_once(
    '    private lateinit var view3d: Golfer3DView\n',
    '    private lateinit var view3d: Golfer3DView\n'
    '    private lateinit var gmailReporter: GmailAutoReporter\n'
    '    private lateinit var gmailSetupButton: Button\n',
    'gmail fields'
)

# Initialize the reporter before UI callbacks can be used.
replace_once(
    '        super.onCreate(savedInstanceState)\n        buildUi()\n',
    '        super.onCreate(savedInstanceState)\n'
    '        gmailReporter = GmailAutoReporter(this) { message ->\n'
    '            runOnUiThread {\n'
    '                Toast.makeText(this, message, Toast.LENGTH_LONG).show()\n'
    '            }\n'
    '        }\n'
    '        buildUi()\n',
    'gmail init'
)

# Add Gmail setup next to 3D view.
replace_once(
    '        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, -2, 1f))\n'
    '        panel.addView(row4)\n',
    '        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, -2, 1f))\n'
    '        gmailSetupButton = button("Gmail設定") { gmailReporter.showSetupDialog() }\n'
    '        row4.addView(gmailSetupButton, LinearLayout.LayoutParams(0, -2, 1f))\n'
    '        panel.addView(row4)\n',
    'gmail button'
)

# One completed five-window scan == one measurement for the mail batch.
replace_once(
    '        consensusReport = combined\n',
    '        consensusReport = combined\n'
    '        recordGmailMeasurement(combined)\n',
    'record completed measurement'
)

# Persist a useful summary for success and failure.
marker = '    private fun captureGlFrame('
idx = s.find(marker)
if idx < 0:
    raise SystemExit("v1.9 captureGlFrame marker missing")

helper = '''    private fun recordGmailMeasurement(report: SlopeReport?) {
        val summary = buildString {
            appendLine("Version: Precision 1.9")
            appendLine("Result: " + if (report == null) "FAIL" else "OK")
            if (report != null) {
                appendLine(String.format(java.util.Locale.JAPAN, "Distance: %.2f m", report.distanceMeters))
                appendLine(String.format(java.util.Locale.JAPAN, "Longitudinal: %.2f %%", report.overallLongitudinalPercent))
                appendLine(String.format(java.util.Locale.JAPAN, "Cross: %.2f %%", report.overallCrossPercent))
                appendLine("Points: " + report.pointCount)
                appendLine("Segments:")
                report.segments.forEachIndexed { index, seg ->
                    appendLine(
                        String.format(
                            java.util.Locale.JAPAN,
                            "  %d: %.2f-%.2fm  long %.2f%%  cross %.2f%%  samples %d",
                            index + 1,
                            seg.startMeters,
                            seg.endMeters,
                            seg.longitudinalPercent,
                            seg.crossPercent,
                            seg.sampleCount
                        )
                    )
                }
            }
            appendLine("Diagnostic: " + precisionLastDiagnostic)
            val surface = precisionSurface
            if (surface != null) {
                appendLine("Precision surface: raw=" + surface.sourcePointCount +
                    " ground=" + surface.groundCellCount +
                    " candidate=" + surface.candidateCellCount +
                    " rejected=" + surface.rejectedCellCount +
                    " frames=" + surface.uniqueFrames)
            }
        }
        runOnUiThread {
            gmailReporter.recordMeasurement(summary)
        }
    }

'''
s = s[:idx] + helper + s[idx:]

# Return Google authorization result to GmailAutoReporter.
resume_marker = '    override fun onResume() {'
idx = s.find(resume_marker)
if idx < 0:
    raise SystemExit("v1.9 onResume marker missing")
activity_result = '''    @Deprecated("Legacy result API is used for Google AuthorizationClient resolution")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (this::gmailReporter.isInitialized) {
            gmailReporter.handleActivityResult(requestCode, resultCode, data)
        }
    }

'''
s = s[:idx] + activity_result + s[idx:]

s = s.replace('appVersion = "Precision 1.8"', 'appVersion = "Precision 1.9"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 180', 'versionCode = 190')
b = b.replace('versionName = "1.8"', 'versionName = "1.9"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v1.9 Gmail auto-report integration")
