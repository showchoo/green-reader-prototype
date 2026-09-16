from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"v0.7.8 patch target not found: {label}")
    return text.replace(old, new, 1)


main_path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
main = main_path.read_text(encoding="utf-8")

main = replace_once(
    main,
    "    private var capturedCupScreen: PointF? = null\n",
    "    private var capturedCupScreen: PointF? = null\n"
    "    private var capturedPositiveCrossScreen: PointF? = null\n",
    "capture field",
)

main = replace_once(
    main,
    "        capturedCupScreen = null\n",
    "        capturedCupScreen = null\n        capturedPositiveCrossScreen = null\n",
    "reset cross direction",
)

main = replace_once(
    main,
    "                val projectedCup = cup?.let { projectWorldPoint(f.camera, it) }\n",
    "                val projectedCup = cup?.let { projectWorldPoint(f.camera, it) }\n"
    "                val projectedCross = if (ball != null && cup != null) {\n"
    "                    projectPositiveCrossDirection(f.camera, ball!!, cup!!)\n"
    "                } else null\n",
    "capture projected +t direction",
)

main = replace_once(
    main,
    "                capturedCupScreen = projectedCup\n",
    "                capturedCupScreen = projectedCup\n                capturedPositiveCrossScreen = projectedCross\n",
    "store projected +t direction",
)

helper = r'''
    /**
     * Project SlopeAnalyzer's +t axis into the actual captured screen.
     *
     * SlopeAnalyzer defines +t as (-uz, +ux) in world X/Z. The previous overlay
     * assumed that +t always appeared on the left side of the displayed putt
     * line. That assumption flips when the camera is viewed from another yaw/
     * roll orientation. Projecting the same world-space basis used by the slope
     * fit keeps the cyan downhill arrows and uphill aim point physically aligned.
     */
    private fun projectPositiveCrossDirection(camera: Camera, ball: Vec3, cup: Vec3): PointF? {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val dist = kotlin.math.sqrt(dx * dx + dz * dz)
        if (dist < 0.05f) return null
        val ux = dx / dist
        val uz = dz / dist
        val vx = -uz
        val vz = ux
        val mid = Vec3(
            (ball.x + cup.x) * 0.5f,
            (ball.y + cup.y) * 0.5f,
            (ball.z + cup.z) * 0.5f
        )
        val side = Vec3(mid.x + vx * 0.35f, mid.y, mid.z + vz * 0.35f)
        val p0 = projectWorldPoint(camera, mid) ?: return null
        val p1 = projectWorldPoint(camera, side) ?: return null
        val sx = p1.x - p0.x
        val sy = p1.y - p0.y
        val len = kotlin.math.sqrt(sx * sx + sy * sy)
        if (len < 1f) return null
        return PointF(sx / len, sy / len)
    }

'''
main = replace_once(
    main,
    "    private fun updateDiagnostics() {\n",
    helper + "    private fun updateDiagnostics() {\n",
    "screen cross projection helper",
)

main = replace_once(
    main,
    "            overlayView.setResult(image, bp, cp, report, adv)\n",
    "            overlayView.setResult(image, bp, cp, report, adv, capturedPositiveCrossScreen)\n",
    "overlay setResult cross direction",
)

main_path.write_text(main, encoding="utf-8")

overlay_path = Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt")
overlay = overlay_path.read_text(encoding="utf-8")

overlay = replace_once(
    overlay,
    "    var advice: PuttAdvisor.Advice? = null\n        private set\n",
    "    var advice: PuttAdvisor.Advice? = null\n        private set\n"
    "    private var positiveCrossScreen: PointF? = null\n",
    "overlay cross field",
)

overlay = replace_once(
    overlay,
    "        slopeReport: SlopeReport,\n        puttAdvice: PuttAdvisor.Advice\n    ) {\n",
    "        slopeReport: SlopeReport,\n        puttAdvice: PuttAdvisor.Advice,\n        positiveCrossDirection: PointF? = null\n    ) {\n",
    "setResult signature",
)

overlay = replace_once(
    overlay,
    "        report = slopeReport\n        advice = puttAdvice\n        invalidate()\n",
    "        report = slopeReport\n        advice = puttAdvice\n        positiveCrossScreen = positiveCrossDirection?.let { PointF(it.x, it.y) }\n        invalidate()\n",
    "store projected cross direction",
)

overlay = replace_once(
    overlay,
    "        advice = null\n        invalidate()\n",
    "        advice = null\n        positiveCrossScreen = null\n        invalidate()\n",
    "clear projected cross direction",
)

overlay = replace_once(
    overlay,
    "        val nx = uy\n        val ny = -ux\n",
    "        // +t follows the measured world-space slope basis projected into the\n"
    "        // captured image. Legacy line-normal fallback is retained only when\n"
    "        // the projection is unavailable.\n"
    "        val projectedCross = positiveCrossScreen\n"
    "        val nx = projectedCross?.x ?: uy\n"
    "        val ny = projectedCross?.y ?: -ux\n",
    "use projected cross direction",
)

overlay_path.write_text(overlay, encoding="utf-8")

print("Applied v0.7.8 screen-space cross-slope projection fix")
