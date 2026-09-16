from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.1 pattern not found ({label}):\n{old[:700]}")
    s = s.replace(old, new, 1)


replace_once(
    "    private var capturedPositiveCrossScreen: PointF? = null\n",
    """    private var capturedPositiveCrossScreen: PointF? = null
    private var ballAnchor: Anchor? = null
    private var cupAnchor: Anchor? = null
""",
    "anchor fields",
)

# Scans must only start when both physical marks are represented by live Anchors.
replace_once(
    """            if (ball == null || cup == null) {
                status.text = "先にボールとカップを設定してください"
                return
            }
            pendingMark = null
""",
    """            if (ball == null || cup == null) {
                status.text = "先にボールとカップを設定してください"
                return
            }
            if (ballAnchor?.trackingState != TrackingState.TRACKING ||
                cupAnchor?.trackingState != TrackingState.TRACKING) {
                status.text = "位置追跡を準備中です。端末を少し動かしてから再試行してください"
                return
            }
            pendingMark = null
""",
    "scan anchor requirement",
)

# requestCaptureAndAnalyze has the same initial mark check; add the live-anchor check there too.
replace_once(
    """        if (ball == null || cup == null) {
            status.text = "先にボールとカップを設定してください"
            return
        }
        pendingMark = null
        scanning = false
""",
    """        if (ball == null || cup == null) {
            status.text = "先にボールとカップを設定してください"
            return
        }
        if (ballAnchor?.trackingState != TrackingState.TRACKING ||
            cupAnchor?.trackingState != TrackingState.TRACKING) {
            status.text = "位置追跡を準備中です。端末を少し動かしてから再試行してください"
            return
        }
        pendingMark = null
        scanning = false
""",
    "capture anchor requirement",
)

# Detach old Anchors on a full reset so later scans cannot accidentally reuse stale poses.
replace_once(
    """        ball = null
        cup = null
        grain = null
""",
    """        ballAnchor?.detach()
        cupAnchor?.detach()
        ballAnchor = null
        cupAnchor = null
        ball = null
        cup = null
        grain = null
""",
    "reset anchors",
)

# Accumulating raw ARCore world coordinates across frames is invalid because ARCore may
# refine/rebase world space between frames. Convert every depth point to the current ball
# Anchor local frame before adding it to the persistent point cloud.
replace_once(
    """            if (scanning && f.camera.trackingState == TrackingState.TRACKING) {
                collector.integrate(f, pixelStrideStep = 4)
                maybeAutoFinishScan()
            }
""",
    """            if (scanning && f.camera.trackingState == TrackingState.TRACKING) {
                val referenceAnchor = ballAnchor
                if (referenceAnchor?.trackingState == TrackingState.TRACKING) {
                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)
                    maybeAutoFinishScan()
                }
            }
""",
    "anchor-local depth integration",
)

# Use current Anchor poses for the captured overlay instead of stale world coordinates
# from the frame where the user originally tapped the ball/cup.
replace_once(
    """                val bitmap = captureGlFrame(viewportW, viewportH)
                val projectedBall = ball?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = cup?.let { projectWorldPoint(f.camera, it) }
                val projectedCross = if (ball != null && cup != null) {
                    projectPositiveCrossDirection(f.camera, ball!!, cup!!)
                } else null
""",
    """                val bitmap = captureGlFrame(viewportW, viewportH)
                val worldMarks = currentWorldMarks()
                val projectedBall = worldMarks?.first?.let { projectWorldPoint(f.camera, it) }
                val projectedCup = worldMarks?.second?.let { projectWorldPoint(f.camera, it) }
                val projectedCross = worldMarks?.let {
                    projectPositiveCrossDirection(f.camera, it.first, it.second)
                }
""",
    "capture current anchor positions",
)

# Auto-finish analysis must use the same coordinate frame as the accumulated point cloud.
replace_once(
    """        val b = ball ?: return
        val c = cup ?: return

        if (elapsed >= 1000L && frameCounter % 6 == 0) {
""",
    """        val marks = currentAnalysisMarks() ?: return
        val b = marks.first
        val c = marks.second

        if (elapsed >= 1000L && frameCounter % 6 == 0) {
""",
    "auto-finish local marks",
)

# Recreate each tap as a persistent Anchor. The raw Vec3 is kept only as a UI fallback;
# all multi-frame calculations below use Anchor-local coordinates.
replace_once(
    """    private fun applyMark(mode: Int, p: Vec3) {
        pendingMark = null
        markMode = 0
        if (mode == 1) {
            ball = p
            status.text = "ボール位置を設定しました。次にカップを設定"
        } else {
            cup = p
            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        if (testMode) updateDiagnostics()
    }
""",
    """    private fun applyMark(mode: Int, p: Vec3) {
        pendingMark = null
        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (_: Throwable) {
            null
        }
        if (newAnchor == null) {
            markMode = mode
            status.text = "位置を固定できませんでした。端末を少し動かしてもう一度タップしてください"
            return
        }

        markMode = 0
        collector.clear()
        if (mode == 1) {
            ballAnchor?.detach()
            ballAnchor = newAnchor
            ball = p
            status.text = "ボール位置を設定しました。次にカップを設定"
        } else {
            cupAnchor?.detach()
            cupAnchor = newAnchor
            cup = p
            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        if (testMode) updateDiagnostics()
    }
""",
    "create persistent anchors",
)

helpers = r'''
    /** Current physical marks in the latest ARCore world frame, for screen projection only. */
    private fun currentWorldMarks(): Pair<Vec3, Vec3>? {
        val bAnchor = ballAnchor ?: return null
        val cAnchor = cupAnchor ?: return null
        if (bAnchor.trackingState != TrackingState.TRACKING ||
            cAnchor.trackingState != TrackingState.TRACKING) return null
        val bt = bAnchor.pose.translation
        val ct = cAnchor.pose.translation
        return Vec3(bt[0], bt[1], bt[2]) to Vec3(ct[0], ct[1], ct[2])
    }

    /**
     * Ball/cup positions in the persistent ball-Anchor coordinate frame.
     * DepthCollector stores every frame in exactly this frame as well.
     */
    private fun currentAnalysisMarks(): Pair<Vec3, Vec3>? {
        val bAnchor = ballAnchor ?: return null
        val cAnchor = cupAnchor ?: return null
        if (bAnchor.trackingState != TrackingState.TRACKING ||
            cAnchor.trackingState != TrackingState.TRACKING) return null
        val worldToBall = bAnchor.pose.inverse()
        val bt = worldToBall.transformPoint(bAnchor.pose.translation)
        val ct = worldToBall.transformPoint(cAnchor.pose.translation)
        return Vec3(bt[0], bt[1], bt[2]) to Vec3(ct[0], ct[1], ct[2])
    }

'''
replace_once(
    "    private fun maybeAutoFinishScan() {\n",
    helpers + "    private fun maybeAutoFinishScan() {\n",
    "anchor coordinate helpers",
)

# Final analysis/logging also has to use Anchor-local marks, otherwise the point cloud
# and endpoints would be expressed in different coordinate systems.
replace_once(
    """        val b = ball
        val c = cup
        if (b == null || c == null) {
            if (updateStatus) status.text = "先にボールとカップを設定してください"
            return
        }
        val report = SlopeAnalyzer.analyze(collector.snapshot(), b, c)
""",
    """        val marks = currentAnalysisMarks()
        if (marks == null) {
            if (updateStatus) status.text = "位置追跡が不安定です。端末を少し動かして再試行してください"
            return
        }
        val b = marks.first
        val c = marks.second
        val report = SlopeAnalyzer.analyze(collector.snapshot(), b, c)
""",
    "final local marks",
)

path.write_text(s, encoding="utf-8")
print("Applied v0.8.1 Anchor-local multi-frame coordinates")
