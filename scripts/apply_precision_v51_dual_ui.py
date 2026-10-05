"""v7.1: split user-facing quality UI from developer diagnostics without removing test telemetry."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"v7.1 {label}: expected 1 target, got {count}")
    s = s.replace(old, new, 1)

old_label = r'''    private fun updatePrecisionRecordLabel() {
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

new_label = r'''    private fun updatePrecisionRecordLabel() {
        if (!::precisionRecordLabel.isInitialized) return
        val q = precisionCurrentQuality
        val qualityText = if (q == null) {
            "測定信頼度 --"
        } else {
            val qualityLabel = when (q.tier) {
                jp.example.greenreader.precision.PrecisionScanQuality.TIER_HIGH_PRECISION -> "高精度"
                jp.example.greenreader.precision.PrecisionScanQuality.TIER_STANDARD -> "標準"
                else -> "再測定推奨"
            }
            "測定信頼度 " + q.score + "/100  " + qualityLabel +
                "\n推定誤差 ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%"
        }
        precisionRecordLabel.text =
            "Putt " + String.format("%03d", precisionPuttId) +
                "  /  Scan " + String.format("%02d", precisionScanIndex) +
                "\n" + qualityText
    }
'''
once(old_label, new_label, "user-safe quality label")

# Keep technical telemetry available, but make it explicitly developer-only.
once('text = "テストモード"', 'text = "開発者診断"', "developer diagnostics label")
once('testToggleButton = button("診断") { toggleTestMode() }',
     'testToggleButton = button("開発者診断") { toggleTestMode() }',
     "developer diagnostics button")

# Version bump. All detailed field telemetry remains in the saved logs and
# diagnostic mode; only the normal UI wording is simplified.
if "Precision 7.0" not in s:
    raise SystemExit("v7.1 source version target missing")
s = s.replace("Precision 7.0", "Precision 7.1")

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "7.0"') != 1 or g.count('versionCode = 700') != 1:
    raise SystemExit("v7.1 Gradle version target missing")
g = g.replace('versionName = "7.0"', 'versionName = "7.1"', 1)
g = g.replace('versionCode = 700', 'versionCode = 710', 1)

assert "測定信頼度 " in s
assert "推定誤差 ±" in s
assert "開発者診断" in s
assert '"QUALITY "' not in new_label
assert '"SESSION "' not in new_label
assert "precisionLastDiagnostic" in s
assert "copyLastPrecisionDiagnostic()" in s
assert "ScanFieldRecorder.saveGrouped(" in s

main.write_text(s, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v7.1 user/developer diagnostics split")
