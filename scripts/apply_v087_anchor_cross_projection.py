from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.7 pattern not found ({label}):\n{old[:900]}")
    s = s.replace(old, new, 1)


# v0.8.1 moved slope analysis into the persistent ball-Anchor local frame, but the
# screen-space +t basis introduced in v0.7.8 was still reconstructed directly from
# current world X/Z. If ARCore refines/rebases world orientation, the fitted cross
# slope sign and the displayed cyan direction can therefore refer to different axes.
# Project the exact +t axis used by SlopeAnalyzer from ball-Anchor local space back
# into the current world frame before projecting it into the captured image.
old_capture = '''                val bitmap = captureGlFrame(viewportW, viewportH)
                val worldMarks = currentWorldMarks()
                val projectedBall = worldMarks?.first?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = worldMarks?.second?.let { projectWorldPoint(f.camera, it) }
                val projectedCross = worldMarks?.let {
                    projectPositiveCrossDirection(f.camera, it.first, it.second)
                }
'''
new_capture = '''                val bitmap = captureGlFrame(viewportW, viewportH)
                val worldMarks = currentWorldMarks()
                val analysisMarks = currentAnalysisMarks()
                val referencePose = ballAnchor?.pose
                val projectedBall = worldMarks?.first?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = worldMarks?.second?.let { projectWorldPoint(f.camera, it) }
                val projectedCross = if (analysisMarks != null && referencePose != null) {
                    projectPositiveCrossDirection(
                        f.camera,
                        referencePose,
                        analysisMarks.first,
                        analysisMarks.second
                    )
                } else null
'''
replace_once(old_capture, new_capture, "capture cross basis in anchor frame")

old_helper = r'''    /**
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
new_helper = r'''    /**
     * Project SlopeAnalyzer's +t axis into the captured screen using the exact
     * coordinate frame in which the depth cloud and slope fit were calculated.
     *
     * SlopeAnalyzer receives ball/cup in ball-Anchor local coordinates and defines
     * +t = (-uz, +ux) there. Convert two local points on that axis through the
     * current Anchor pose before camera projection. This keeps crossPercent's sign
     * and the cyan downhill arrows aligned even after ARCore rebases/rotates world
     * coordinates while tracking.
     */
    private fun projectPositiveCrossDirection(
        camera: Camera,
        referencePose: Pose,
        ballLocal: Vec3,
        cupLocal: Vec3
    ): PointF? {
        val dx = cupLocal.x - ballLocal.x
        val dz = cupLocal.z - ballLocal.z
        val dist = kotlin.math.sqrt(dx * dx + dz * dz)
        if (dist < 0.05f) return null
        val ux = dx / dist
        val uz = dz / dist
        val vx = -uz
        val vz = ux

        val midLocal = floatArrayOf(
            (ballLocal.x + cupLocal.x) * 0.5f,
            (ballLocal.y + cupLocal.y) * 0.5f,
            (ballLocal.z + cupLocal.z) * 0.5f
        )
        val sideLocal = floatArrayOf(
            midLocal[0] + vx * 0.35f,
            midLocal[1],
            midLocal[2] + vz * 0.35f
        )
        val midWorldRaw = referencePose.transformPoint(midLocal)
        val sideWorldRaw = referencePose.transformPoint(sideLocal)
        val midWorld = Vec3(midWorldRaw[0], midWorldRaw[1], midWorldRaw[2])
        val sideWorld = Vec3(sideWorldRaw[0], sideWorldRaw[1], sideWorldRaw[2])
        val p0 = projectWorldPoint(camera, midWorld) ?: return null
        val p1 = projectWorldPoint(camera, sideWorld) ?: return null
        val sx = p1.x - p0.x
        val sy = p1.y - p0.y
        val len = kotlin.math.sqrt(sx * sx + sy * sy)
        if (len < 1f) return null
        return PointF(sx / len, sy / len)
    }

'''
replace_once(old_helper, new_helper, "anchor-local cross projection helper")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.7 Anchor-local cross-axis screen projection")
