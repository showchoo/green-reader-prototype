from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")

old = '''        if (updateStatus) {
            val dir = if (adv.aimOffsetCm >= 0) "左" else "右"
            status.text = String.format(
                "解析完了: %.2fm / 縦 %.1f%% / 横 %.1f%% / %s %.0fcm狙い / 点%d",
                report.distanceMeters,
                report.overallLongitudinalPercent,
                report.overallCrossPercent,
                dir,
                kotlin.math.abs(adv.aimOffsetCm),
                report.pointCount
            )
            if (showResult) {'''

new = '''        if (updateStatus) {
            if (testMode) {
                val dir = if (adv.aimOffsetCm >= 0) "左" else "右"
                status.text = String.format(
                    "診断: %.2fm / 縦 %.1f%% / 横 %.1f%% / %s %.0fcm / 点%d",
                    report.distanceMeters,
                    report.overallLongitudinalPercent,
                    report.overallCrossPercent,
                    dir,
                    kotlin.math.abs(adv.aimOffsetCm),
                    report.pointCount
                )
            } else {
                status.text = "解析完了　白線=予測ライン / 黄色=狙い / 水色=下り方向"
            }
            if (showResult) {'''

if old not in s:
    raise SystemExit("v0.7.2 result-status pattern not found")

s = s.replace(old, new, 1)
path.write_text(s, encoding="utf-8")
print("Applied v0.7.2 clean result status")
