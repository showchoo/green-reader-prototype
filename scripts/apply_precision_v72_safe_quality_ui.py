"""Precision v7.2: simplify normal quality UI while preserving full developer diagnostics."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

def once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"v7.2 {label}: expected 1 target, got {count}")
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
                "  /  HOLE " + String.format("%02d", precisionHoleNumber) +
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
                jp.example.greenreader.precision.PrecisionQualityEstimator.TIER_HIGH_PRECISION -> "高精度"
                jp.example.greenreader.precision.PrecisionQualityEstimator.TIER_STANDARD -> "標準"
                else -> "再測定推奨"
            }
            "測定信頼度 " + q.score + "/100  " + qualityLabel +
                "\n推定誤差 ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%"
        }
        precisionRecordLabel.text =
            "Hole " + String.format("%02d", precisionHoleNumber) +
                "  /  Putt " + String.format("%03d", precisionPuttId) +
                "  /  Scan " + String.format("%02d", precisionScanIndex) +
                "\n" + qualityText
    }
'''
once(old_label, new_label, "normal quality label")

# Make the technical panel explicitly developer-only. The telemetry remains
# intact and is still written to the field packages for validation.
once('text = "テストモード"', 'text = "開発者診断"', "developer diagnostics label")
once('testToggleButton = button("診断") { toggleTestMode() }',
     'testToggleButton = button("開発者診断") { toggleTestMode() }',
     "developer diagnostics button")

# Version bump only; measurement math and v7.1 field-recording behavior stay unchanged.
if "Precision 7.1" not in s:
    raise SystemExit("v7.2 source version target missing")
s = s.replace("Precision 7.1", "Precision 7.2")

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "7.1"') != 1 or g.count('versionCode = 710') != 1:
    raise SystemExit("v7.2 Gradle version target missing")
g = g.replace('versionName = "7.1"', 'versionName = "7.2"', 1)
g = g.replace('versionCode = 710', 'versionCode = 720', 1)

# Product UI is simplified...
assert "測定信頼度 " in s
assert "推定誤差 ±" in s
assert "開発者診断" in s
assert '"SESSION "' not in new_label
assert '"QUALITY "' not in new_label

# ...while all v7.1 field-test and technical diagnostics remain present.
assert 'button("次のホール")' in s
assert 'button("結果入力")' in s
assert "ScanFieldRecorder.savePuttResult" in s
assert "bitmap = failureBitmap" in s
assert "precisionLastDiagnostic" in s
assert "copyLastPrecisionDiagnostic()" in s
assert "PrecisionQualityEstimator.evaluate(" in s
assert "precisionTrackingMonitor.observe(" in s
assert "precisionCollectorWindowSnapshots" in s
assert "ScanFieldRecorder.saveGrouped(" in s
assert "ScanFieldRecorder.saveFailureGrouped(" in s

main.write_text(s, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v7.2 user-safe quality UI on top of v7.1")
