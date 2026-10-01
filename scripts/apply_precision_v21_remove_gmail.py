from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def remove_once(text: str, label: str):
    global s
    if text not in s:
        raise SystemExit(f"v2.1 removal target missing: {label}")
    s = s.replace(text, "", 1)

remove_once(
    '    private lateinit var gmailReporter: GmailAutoReporter\n'
    '    private lateinit var gmailSetupButton: Button\n',
    'gmail fields'
)

remove_once(
    '        gmailReporter = GmailAutoReporter(this) { message ->\n'
    '            runOnUiThread {\n'
    '                Toast.makeText(this, message, Toast.LENGTH_LONG).show()\n'
    '            }\n'
    '        }\n',
    'gmail init'
)

remove_once(
    '        gmailSetupButton = button("Gmail設定") { gmailReporter.showSetupDialog() }\n'
    '        row4.addView(gmailSetupButton, LinearLayout.LayoutParams(0, -2, 1f))\n',
    'gmail button'
)

remove_once(
    '        recordGmailMeasurement(combined)\n',
    'gmail record call'
)

start = s.find('    private fun recordGmailMeasurement(report: SlopeReport?) {')
end_marker = '    private fun captureGlFrame('
end = s.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("v2.1 gmail helper block missing")
s = s[:start] + s[end:]

start = s.find('    @Deprecated("Legacy result API is used for Google AuthorizationClient resolution")')
end = s.find('    override fun onResume() {', start)
if start < 0 or end < 0:
    raise SystemExit("v2.1 activity result block missing")
s = s[:start] + s[end:]

s = s.replace('appVersion = "Precision 2.0"', 'appVersion = "Precision 2.1"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 200', 'versionCode = 210')
b = b.replace('versionName = "2.0"', 'versionName = "2.1"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v2.1: Gmail/OAuth fully removed")
