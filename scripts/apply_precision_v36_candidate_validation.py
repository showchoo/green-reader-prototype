"""v5.6: reject unsuitable candidates before short-circuiting the tap pipeline."""
from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")


def once(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit(f"v5.6 expected one target: {old[:150]}")
    s = s.replace(old, new, 1)


def replace_function(name, body):
    global s
    start = s.index(f"    private fun {name}(")
    end = s.index("\n    private fun ", start + 20)
    s = s[:start] + body.rstrip() + "\n" + s[end:]


once("import jp.example.greenreader.precision.PrecisionSlopeAnalyzer\n",
     "import jp.example.greenreader.precision.PrecisionSlopeAnalyzer\n"
     "import jp.example.greenreader.precision.PrecisionMarkerCandidateGate\n")
once('Precision 5.5 TAP', 'Precision 5.6 TAP')
once('appVersion = "Precision 5.5"', 'appVersion = "Precision 5.6"')

once('''        precisionTapTrace.append("camera tracking=${f.camera.trackingState} timestamp=${f.timestamp}\\n")
''', '''        precisionTapTrace.append("camera tracking=${f.camera.trackingState} timestamp=${f.timestamp} world=${f.camera.pose.translation.contentToString()}\\n")
        if (mode == 2) {
            val reference = ballAnchor
            precisionTapTrace.append("ball reference tracking=${reference?.trackingState} world=${reference?.pose?.translation?.contentToString()}\\n")
            if (reference?.trackingState != TrackingState.TRACKING) {
                status.text = "ボール位置の追跡を確認できません。追跡復帰後にカップをタップしてください"
                finishPrecisionTap(mode, false)
                return
            }
        }
''')

once('''        val c = frame.camera.pose.translation
        val dx = p.x - c[0]
        val dy = p.y - c[1]
        val dz = p.z - c[2]
        val d2 = dx * dx + dy * dy + dz * dz
        val accepted = d2.isFinite() && d2 in 0.04f..16.0f
        precisionTapTrace.append("$source world=(${p.x},${p.y},${p.z}) cameraDistance=${kotlin.math.sqrt(d2)} accepted=$accepted\\n")
        return if (accepted) p else null
''', '''        val c = frame.camera.pose.translation
        val reference = if (markMode == 2) ballAnchor else null
        if (markMode == 2 && reference?.trackingState != TrackingState.TRACKING) {
            precisionTapTrace.append("$source rejected=ball-not-tracking\\n")
            return null
        }
        val bt = reference?.pose?.translation
        val ballPoint = bt?.let { Vec3(it[0], it[1], it[2]) }
        val gate = PrecisionMarkerCandidateGate.evaluate(Vec3(c[0], c[1], c[2]), p, ballPoint)
        precisionTapTrace.append("$source world=(${p.x},${p.y},${p.z}) cameraDistance=${gate.cameraDistance} accepted=${gate.accepted} reason=${gate.reason ?: "ok"} horizontal=${gate.horizontal} vertical=${gate.vertical} limit=${gate.limit}\\n")
        return if (gate.accepted) p else null
''')

replace_function("exactSurfaceHitPoint", r'''    private fun exactSurfaceHitPoint(frame: Frame, x: Float, y: Float): Vec3? {
        return admissibleSurfaceHit(frame, x, y, "exactSurface")
    }

    private fun admissibleSurfaceHit(frame: Frame, x: Float, y: Float, source: String): Vec3? {
        val hits = frame.hitTest(x, y)
        precisionTapTrace.append("$source hits=${hits.size} at=($x,$y)\n")
        for ((index, hit) in hits.withIndex()) {
            val trackable = hit.trackable
            val type = if (trackable is Plane) "Plane/${trackable.type}" else trackable.javaClass.simpleName
            val tr = hit.hitPose.translation
            val reason = when {
                trackable.trackingState != TrackingState.TRACKING -> "not-tracking"
                trackable is Plane && trackable.type != Plane.Type.HORIZONTAL_UPWARD_FACING -> "not-upward-plane"
                trackable is Plane && !trackable.isPoseInPolygon(hit.hitPose) -> "outside-polygon"
                trackable !is Plane && trackable !is DepthPoint -> "unsupported-type"
                else -> null
            }
            precisionTapTrace.append("$source hit=$index type=$type tracking=${trackable.trackingState} world=${tr.contentToString()} reject=${reason ?: "none"}\n")
            if (reason != null) continue
            // Check each hit BEFORE first-success selection. A closer but
            // vertically inconsistent hit must not hide a valid later hit.
            val point = tracedMarkCandidate(frame, "$source/$index/$type") {
                Vec3(tr[0], tr[1], tr[2])
            }
            if (point != null) return point
        }
        return null
    }
''')

replace_function("tinyNearbyHitPoint", r'''    private fun tinyNearbyHitPoint(frame: Frame, x: Float, y: Float): Vec3? {
        val offsets = arrayOf(
            10f to 0f, -10f to 0f, 0f to 10f, 0f to -10f,
            10f to 10f, 10f to -10f, -10f to 10f, -10f to -10f,
            20f to 0f, -20f to 0f, 0f to 20f, 0f to -20f
        )
        for ((dx, dy) in offsets) {
            val sx = (x + dx).coerceIn(0f, viewportW.toFloat() - 1f)
            val sy = (y + dy).coerceIn(0f, viewportH.toFloat() - 1f)
            val point = admissibleSurfaceHit(frame, sx, sy, "nearbySurface[$dx,$dy]")
            if (point != null) return point
        }
        return null
    }
''')

# Keep the post-Anchor check: pose refinement may occur after candidate selection.
assert "vertical > limit" in s
assert "markMode = 2" in s
gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
assert g.count('versionName = "5.5"') == 1
assert g.count('versionCode = 550') == 1
g = g.replace('versionName = "5.5"', 'versionName = "5.6"')
g = g.replace('versionCode = 550', 'versionCode = 560')
p.write_text(s, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v5.6 candidate type/height validation before fallback selection")
