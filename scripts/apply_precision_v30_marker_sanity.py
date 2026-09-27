from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

old='''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        // Prefer ARCore tracked physical surfaces. Depth is only a fallback:
        // Full Depth may contain completed/background geometry along the tap ray.
        return exactSurfaceHitPoint(frame, x, y)
            ?: tinyNearbyHitPoint(frame, x, y)
            ?: depthPointAtTap(frame, x, y)
    }
'''
new='''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        fun plausible(p: Vec3?): Vec3? {
            p ?: return null
            val c = frame.camera.pose.translation
            val dx = p.x - c[0]
            val dy = p.y - c[1]
            val dz = p.z - c[2]
            val d2 = dx * dx + dy * dy + dz * dz
            return if (d2.isFinite() && d2 in 0.04f..16.0f) p else null
        }

        // Prefer tracked physical surfaces, but apply the same 4 m sanity gate
        // to every path, including Full Depth fallbacks.
        return plausible(exactSurfaceHitPoint(frame, x, y))
            ?: plausible(tinyNearbyHitPoint(frame, x, y))
            ?: plausible(depthPointAtTap(frame, x, y))
    }
'''
if old not in s:
    raise SystemExit("v4.4 target missing: resolveMarkPoint")
s=s.replace(old,new,1)

old2='''        val bt = levelFrame.worldToLocal(bAnchor.pose.translation)
        val ct = levelFrame.worldToLocal(cAnchor.pose.translation)
        return Vec3(bt[0], bt[1], bt[2]) to Vec3(ct[0], ct[1], ct[2])
'''
new2='''        val bt = levelFrame.worldToLocal(bAnchor.pose.translation)
        val ct = levelFrame.worldToLocal(cAnchor.pose.translation)

        // Validate vertical separation against the horizontal ball-cup
        // distance. A fixed 35 cm gate was too permissive for short putts:
        // e.g. 32 cm horizontally and 33 cm vertically could slip through.
        val markDx = ct[0] - bt[0]
        val markDz = ct[2] - bt[2]
        val horizontalDistance = kotlin.math.sqrt(markDx * markDx + markDz * markDz)
        val verticalDifference = kotlin.math.abs(ct[1] - bt[1])
        val maxVerticalDifference = kotlin.math.max(
            0.08f,
            horizontalDistance * 0.12f + 0.04f
        )
        if (!horizontalDistance.isFinite() || !verticalDifference.isFinite()) {
            precisionLastDiagnostic =
                "MARK invalid-number horizontal=" + String.format("%.3f", horizontalDistance) +
                " vertical=" + String.format("%.3f", verticalDifference)
            return null
        }
        if (verticalDifference > maxVerticalDifference) {
            precisionLastDiagnostic =
                "MARK vertical-mismatch horizontal=" + String.format("%.3f", horizontalDistance) +
                " vertical=" + String.format("%.3f", verticalDifference) +
                " limit=" + String.format("%.3f", maxVerticalDifference) +
                " ball=(" + String.format("%.2f", bt[0]) + "," +
                    String.format("%.2f", bt[1]) + "," + String.format("%.2f", bt[2]) + ")" +
                " cup=(" + String.format("%.2f", ct[0]) + "," +
                    String.format("%.2f", ct[1]) + "," + String.format("%.2f", ct[2]) + ")"
            return null
        }

        precisionLastDiagnostic =
            "MARK ok horizontal=" + String.format("%.3f", horizontalDistance) +
            " vertical=" + String.format("%.3f", verticalDifference) +
            " limit=" + String.format("%.3f", maxVerticalDifference)

        return Vec3(bt[0], bt[1], bt[2]) to Vec3(ct[0], ct[1], ct[2])
'''
if old2 not in s:
    raise SystemExit("v4.4 target missing: currentAnalysisMarks")
s=s.replace(old2,new2,1)


# Add explicit diagnostics for missing/not-tracking anchors inside currentAnalysisMarks only.
fn_start = s.find("    private fun currentAnalysisMarks(): Pair<Vec3, Vec3>? {")
fn_end = s.find("\n    private fun ", fn_start + 10)
if fn_start < 0 or fn_end < 0:
    raise SystemExit("v5.0 currentAnalysisMarks boundaries missing")
fn = s[fn_start:fn_end]
fn = fn.replace(
    "        val bAnchor = ballAnchor ?: return null\n",
    '        val bAnchor = ballAnchor ?: run { precisionLastDiagnostic = "MARK ballAnchor=null"; return null }\\n',
    1
)
fn = fn.replace(
    "        val cAnchor = cupAnchor ?: return null\n",
    '        val cAnchor = cupAnchor ?: run { precisionLastDiagnostic = "MARK cupAnchor=null"; return null }\\n',
    1
)
old_tracking = """        if (bAnchor.trackingState != TrackingState.TRACKING ||
            cAnchor.trackingState != TrackingState.TRACKING) return null
"""
new_tracking = """        if (bAnchor.trackingState != TrackingState.TRACKING ||
            cAnchor.trackingState != TrackingState.TRACKING) {
            precisionLastDiagnostic =
                "MARK tracking ball=" + bAnchor.trackingState +
                " cup=" + cAnchor.trackingState
            return null
        }
"""
if old_tracking in fn:
    fn = fn.replace(old_tracking, new_tracking, 1)
s = s[:fn_start] + fn + s[fn_end:]

p.write_text(s,encoding="utf-8")
print("Applied Precision v4.4 fail-closed marker validation")
