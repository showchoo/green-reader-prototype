"""Precision v7.9: align the projected cross axis with the gravity frame;
refuse a visible left/right prediction if direction cannot be established.

No arbitrary sign flip. Old 12% physical slope limit and records stay intact.
"""
from pathlib import Path
import re

root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
overlay=root/"ui/CameraOverlayResultView.kt"
mapview=root/"ui/GreenMapView.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
o=overlay.read_text(encoding="utf8")
v=mapview.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit("v7.9 "+label+": wanted exactly one target, found "+str(n))
    return text.replace(old,new,1)

# v1.4 already fixed the anchor-pitch/roll mismatch. Check that
# existing fix remains, rather than introducing a speculative second flip.
assert 'val levelFrame = GravityAlignedFrame.fromPose(referencePose)' in s
assert 'val midWorldRaw = levelFrame.localToWorld(midLocal)' in s
assert 'val sideWorldRaw = levelFrame.localToWorld(sideLocal)' in s
assert 'referencePose.transformPoint(midLocal)' not in s

s=one(s,
'''    private val precisionWindowGlobalSlopes = ArrayList<Pair<Float, Float>?>(8)''',
'''    private val precisionWindowGlobalSlopes = ArrayList<Pair<Float, Float>?>(8)
    private var precisionDirectionTrustworthy = false''',
"direction trust state")

# Never leak a previous scan's trusted direction into this scan.
regex=re.compile(r'(?m)^([ \t]*)precisionWindowGlobalSlopes\.clear\(\)$')
s,n=regex.subn(lambda m:m.group(0)+"\n"+m.group(1)+"precisionDirectionTrustworthy = false",s)
if n < 2:raise SystemExit("v7.9 missing multiple scan reset paths: "+str(n))

s=one(s,
'''        if (precisionTemporalUnstable) combined = null
        consensusReport = combined
        precisionLastDiagnostic += " | " + temporalResult.diagnostic +''',
'''        if (precisionTemporalUnstable) combined = null
        val directionVerdict = jp.example.greenreader.precision.PrecisionDirectionSafety.evaluate(
            combined, precisionWindowGlobalSlopes
        )
        precisionDirectionTrustworthy = directionVerdict.trustworthy
        consensusReport = combined
        precisionLastDiagnostic += " | " + directionVerdict.diagnostic +
            " | " + temporalResult.diagnostic +''',
"direction verification from independent window slopes")

# Never show a directional map when sign agreement was not verified.
# Keep the report for saving, quality analysis and future offline replay.
map_assign = "        mapView.report = report\n"
if s.count(map_assign) != 2:
    raise SystemExit("v7.9 expected two map display assignments")
s = s.replace(map_assign,
    map_assign + "        mapView.directionVerified = precisionDirectionTrustworthy\n")

# Overlay API has always accepted the anchor-relative +t projection.
s=one(s,
'''            overlayView.setResult(image, bp, cp, report, adv, capturedPositiveCrossScreen)''',
'''            overlayView.setResult(
                image, bp, cp, report, adv, capturedPositiveCrossScreen,
                allowDirection = precisionDirectionTrustworthy
            )''',
"captured image direction flag")

# The screen projection cannot be recovered after it is lost; don't select an
# arbitrary left or right normal. Alert, never render a potentially mirrored path.
o=one(o,
'''    private var positiveCrossScreen: PointF? = null''',
'''    private var positiveCrossScreen: PointF? = null
    private var directionVerified = false''',
"overlay direction state")
o=one(o,
'''        positiveCrossDirection: PointF? = null
    ) {''',
'''        positiveCrossDirection: PointF? = null,
        allowDirection: Boolean = false
    ) {''',
"overlay call API")
o=one(o,
'''        positiveCrossScreen = positiveCrossDirection?.let { PointF(it.x, it.y) }
        invalidate()''',
'''        positiveCrossScreen = positiveCrossDirection?.let { PointF(it.x, it.y) }
        directionVerified = allowDirection && positiveCrossDirection != null &&
            positiveCrossDirection.x.isFinite() && positiveCrossDirection.y.isFinite()
        invalidate()''',
"overlay projected basis validation")
o=one(o,
'''        positiveCrossScreen = null
        invalidate()''',
'''        positiveCrossScreen = null
        directionVerified = false
        invalidate()''',
"overlay reset")

needle='''        canvas.drawRect(imageRect, dimPaint)

        fun mapPoint(p: PointF) = PointF(left + p.x * scale, top + p.y * scale)''';
replacement='''        canvas.drawRect(imageRect, dimPaint)

        if (!directionVerified) {
            // Even a dense, repeatable Depth cloud may have the wrong sign.
            // Draw neither an arbitrary hook/slice nor misleading downhill arrows.
            textPaint.textAlign = Paint.Align.CENTER
            textPaint.textSize = 27f
            textPaint.color = Color.rgb(255, 230, 160)
            canvas.drawText("左右方向の判定を保留", width / 2f, height / 2f, textPaint)
            canvas.drawText("スキャンをやり直してください", width / 2f, height / 2f + 36f, textPaint)
            return
        }

        fun mapPoint(p: PointF) = PointF(left + p.x * scale, top + p.y * scale)''';
o=one(o,needle,replacement,"no arbitrary break when projection absent")
# The fallback used a screen-side convention unrelated to fitted +t.
o=one(o,
'''        val nx = projectedCross?.x ?: uy
        val ny = projectedCross?.y ?: -ux''',
'''        val nx = projectedCross!!.x
        val ny = projectedCross.y''',
"verified cross basis in drawing")
# DrawSlopeVectors has a separate basis; keep it same as path and only run
# when the directionVerified check above passed.
o=one(o,
'''        val nx = projectedCross?.x ?: uy
        val ny = projectedCross?.y ?: -ux''',
'''        val nx = projectedCross!!.x
        val ny = projectedCross.y''',
"verified downhill vectors")

v=one(v,
'''    var report: SlopeReport? = null
        set(value) { field = value; invalidate() }''',
'''    var report: SlopeReport? = null
        set(value) { field = value; invalidate() }
    var directionVerified: Boolean = false
        set(value) { field = value; invalidate() }''',
"top-down direction guard field")

v=one(v,
'''        val r = report
        if (r == null) {''',
'''        val r = report
        if (r != null && !directionVerified) {
            textPaint.textAlign = Paint.Align.CENTER
            textPaint.textSize = 24f
            canvas.drawText("左右方向の判定を保留", width / 2f, height / 2f, textPaint)
            canvas.drawText("再スキャンで確認してください", width / 2f, height / 2f + 37f, textPaint)
            return
        }
        if (r == null) {''',
"top-down no dubious roll prediction")

# A pure Kotlin gate permits deterministic unit tests without Android/ARCore.
gate=root/"precision/PrecisionDirectionSafety.kt"
gate.write_text('''package jp.example.greenreader.precision

import jp.example.greenreader.analysis.SlopeReport
import kotlin.math.abs

/**
 * Gate only the DIRECTION of the rendered putt, not the availability of
 * measurements. Cannot detect a systematic Depth bias common to all windows.
 * Every slope is dh/d(right-axis), so positive means higher toward +right.
 */
object PrecisionDirectionSafety {
    data class Verdict(
        val trustworthy: Boolean,
        val reason: String,
        val agreeingWindows: Int,
        val validWindows: Int
    ) {
        val diagnostic: String
            get() = "DIRECTION " + reason +
                " agree=" + agreeingWindows + "/" + validWindows
    }

    fun evaluate(
        report: SlopeReport?,
        independentWindows: List<Pair<Float, Float>?>,
        minAbsCrossPp: Float = 0.8f
    ): Verdict {
        if (report == null) return Verdict(false, "no-report", 0, 0)
        val cross = report.overallCrossPercent
        if (!cross.isFinite() || abs(cross) < minAbsCrossPp) {
            return Verdict(false, "small-or-invalid-cross", 0, 0)
        }
        val reliable = independentWindows.mapNotNull { pair ->
            pair?.second?.takeIf { it.isFinite() && abs(it) >= minAbsCrossPp }
        }
        val agree = reliable.count { it * cross > 0f }
        val oppose = reliable.size - agree

        // A strong reversed window is evidence of possible opposite break;
        // do not declare the direction certain by simple averaging.
        if (reliable.size < 4) {
            return Verdict(false, "few-independent-windows", agree, reliable.size)
        }
        if (oppose > 0) return Verdict(false, "opposing-windows", agree, reliable.size)

        val segments = report.segments
        val significant = segments.filter {
            it.crossPercent.isFinite() && abs(it.crossPercent) >= minAbsCrossPp
        }
        if (significant.size < 4) {
            return Verdict(false, "few-supported-segments", agree, reliable.size)
        }
        val oppositeSegments = significant.count { it.crossPercent * cross < 0f }
        if (oppositeSegments >= 2) {
            return Verdict(false, "opposing-segments", agree, reliable.size)
        }
        return Verdict(true, "supported", agree, reliable.size)
    }
}
''',encoding="utf8")

assert 'MAX_USABLE_SLOPE_PERCENT = 12f' in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert 'button("次のホール")' in s and 'button("結果入力")' in s
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
if 'Precision 7.8' not in s: raise SystemExit("v7.8 must precede v7.9")
s=s.replace('Precision 7.8','Precision 7.9')
g=one(g,'versionName = "7.8"','versionName = "7.9"',"version name")
g=one(g,'versionCode = 780','versionCode = 790',"version code")

main.write_text(s,encoding="utf8")
overlay.write_text(o,encoding="utf8")
mapview.write_text(v,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied v7.9 gravity-projection and fail-closed cross-direction checks")
