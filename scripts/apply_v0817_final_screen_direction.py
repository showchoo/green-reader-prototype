from pathlib import Path

overlay_path = Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt")
s = overlay_path.read_text(encoding="utf-8")

old_aim = '''        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val aimPx = ((a.aimOffsetCm / 100f) * pxPerMeter * crossToRightSign)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)
'''
new_aim = '''        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val renderAimCm = jp.example.greenreader.analysis.DisplayDirectionCalibration
            .renderAimOffsetCm(a.aimOffsetCm, crossToRightSign)
        val aimPx = ((renderAimCm / 100f) * pxPerMeter)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)
'''
if old_aim not in s:
    raise SystemExit("v0.8.17 aim target not found")
s = s.replace(old_aim, new_aim, 1)

old_arrow = '''            val screenCrossPercent = seg.crossPercent * crossToRightSign
            val downhillSign = if (screenCrossPercent >= 0f) -1f else 1f
            val arrowLen = (28f + abs(screenCrossPercent) * 12f).coerceIn(28f, 90f)
'''
new_arrow = '''            val screenCrossPercent = jp.example.greenreader.analysis.DisplayDirectionCalibration
                .renderCrossPercent(seg.crossPercent, crossToRightSign)
            val downhillSign = if (screenCrossPercent >= 0f) -1f else 1f
            val arrowLen = (28f + abs(screenCrossPercent) * 12f).coerceIn(28f, 90f)
'''
if old_arrow not in s:
    raise SystemExit("v0.8.17 arrow target not found")
s = s.replace(old_arrow, new_arrow, 1)

overlay_path.write_text(s, encoding="utf-8")

main_path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
main = main_path.read_text(encoding="utf-8")
if 'appVersion = "0.8.16"' not in main:
    raise SystemExit("v0.8.17 appVersion target not found")
main = main.replace('appVersion = "0.8.16"', 'appVersion = "0.8.17"', 1)
main_path.write_text(main, encoding="utf-8")

print("Applied v0.8.17 final screen-direction field calibration")
