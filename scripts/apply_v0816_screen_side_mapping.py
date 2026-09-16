from pathlib import Path

main_path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
main = main_path.read_text(encoding="utf-8")

old = '''        val rawCombined = SlopeConsensus.combine(consensusReports, minAgree = 4)
        val combined = rawCombined?.let { FieldOrientationCalibration.correctCrossSign(it) }
'''
new = '''        val combined = SlopeConsensus.combine(consensusReports, minAgree = 4)
'''
if old not in main:
    raise SystemExit("v0.8.16 consensus calibration target not found")
main = main.replace(old, new, 1)

if 'appVersion = "0.8.15"' not in main:
    raise SystemExit("v0.8.16 appVersion target not found")
main = main.replace('appVersion = "0.8.15"', 'appVersion = "0.8.16"', 1)
if "FieldOrientationCalibration.correctCrossSign" in main:
    raise SystemExit("v0.8.16 hard-coded cross sign calibration remains")
main_path.write_text(main, encoding="utf-8")

overlay_path = Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt")
s = overlay_path.read_text(encoding="utf-8")

old_basis = '''        // +t follows the measured world-space slope basis projected into the
        // captured image. Legacy line-normal fallback is retained only when
        // the projection is unavailable.
        val projectedCross = positiveCrossScreen
        val nx = projectedCross?.x ?: uy
        val ny = projectedCross?.y ?: -ux

        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val aimPx = ((a.aimOffsetCm / 100f) * pxPerMeter)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)

        val aim = PointF(c.x + nx * aimPx, c.y + ny * aimPx)
'''
new_basis = '''        // Render in one canonical screen coordinate: +cross = the right-hand side
        // of the visible ball->cup line. The AR/local +t axis may project to either
        // screen side, so convert its sign once instead of feeding its raw vector
        // directly to drawing. This prevents a 180-degree left/right inversion.
        val nx = -uy
        val ny = ux
        val crossToRightSign = positiveCrossScreen?.let {
            jp.example.greenreader.analysis.ScreenSideMapper.projectedCrossToScreenRightSign(
                ux, uy, it.x, it.y
            )
        } ?: 1f

        val pxPerMeter = screenDistance / r.distanceMeters.coerceAtLeast(0.2f)
        val aimPx = ((a.aimOffsetCm / 100f) * pxPerMeter * crossToRightSign)
            .coerceIn(-screenDistance * 0.45f, screenDistance * 0.45f)

        val aim = PointF(c.x + nx * aimPx, c.y + ny * aimPx)
'''
if old_basis not in s:
    raise SystemExit("v0.8.16 overlay basis target not found")
s = s.replace(old_basis, new_basis, 1)

old_arrow = '''            val downhillSign = if (seg.crossPercent >= 0f) -1f else 1f
            val arrowLen = (28f + abs(seg.crossPercent) * 12f).coerceIn(28f, 90f)
'''
new_arrow = '''            val screenCrossPercent = seg.crossPercent * crossToRightSign
            val downhillSign = if (screenCrossPercent >= 0f) -1f else 1f
            val arrowLen = (28f + abs(screenCrossPercent) * 12f).coerceIn(28f, 90f)
'''
if old_arrow not in s:
    raise SystemExit("v0.8.16 arrow sign target not found")
s = s.replace(old_arrow, new_arrow, 1)

overlay_path.write_text(s, encoding="utf-8")
print("Applied v0.8.16 canonical screen-right cross mapping")
