"""Precision 7.6: marker consistency, measured distance audit and quick re-tap.

No rescaling of measurements: a reference length only identifies suspicious
marker choices. Tightening the height gate cannot establish ground truth.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
gate=root/"precision/PrecisionMarkerCandidateGate.kt"
geom=root/"precision/PrecisionMarkerGeometry.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
a=gate.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(content,old,new,label):
    found=content.count(old)
    if found!=1: raise SystemExit("v7.6 "+label+": expected one match, got "+str(found))
    return content.replace(old,new,1)

geom.write_text('''package jp.example.greenreader.precision

import jp.example.greenreader.analysis.Vec3
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/** Checks plausibility of two independent AR anchors, not true slope accuracy. */
object PrecisionMarkerGeometry {
    data class Result(
        val horizontalMeters: Float,
        val verticalMeters: Float,
        val nominalGradePercent: Float,
        val referenceDistanceMeters: Float?,
        val referenceErrorMeters: Float?,
        val markerWarning: Boolean,
        val referenceWarning: Boolean
    ) {
        val needsReview: Boolean get() = markerWarning || referenceWarning
    }

    fun maxVerticalDifference(horizontalMeters: Float): Float =
        max(0.06f, horizontalMeters * 0.12f + 0.01f)

    fun evaluate(ball: Vec3, cup: Vec3, referenceMeters: Float? = null): Result {
        val dx = cup.x - ball.x
        val dz = cup.z - ball.z
        val horizontal = sqrt(dx * dx + dz * dz)
        val vertical = cup.y - ball.y
        val grade = if (horizontal >= 0.01f) vertical / horizontal * 100f else Float.NaN
        val validReference = referenceMeters?.takeIf { it.isFinite() && it >= 0.4f && it <= 12f }
        val error = validReference?.let { horizontal - it }
        return Result(
            horizontalMeters = horizontal,
            verticalMeters = vertical,
            nominalGradePercent = grade,
            referenceDistanceMeters = validReference,
            referenceErrorMeters = error,
            markerWarning = !horizontal.isFinite() || !vertical.isFinite() ||
                horizontal < 0.4f || abs(vertical) > maxVerticalDifference(horizontal),
            referenceWarning = error != null &&
                (!error.isFinite() || abs(error) > max(0.06f, validReference * 0.05f))
        )
    }
}
''',encoding="utf8")

# The candidate gate and final anchored check must agree; a conflicting
# Plane hit can now be rejected in favor of another candidate at the tap.
a=one(a,
    "val limit = max(0.08f, horizontal * 0.12f + 0.04f)",
    "val limit = PrecisionMarkerGeometry.maxVerticalDifference(horizontal)",
    "candidate gate height limit")
s=one(s,
    "val limit = kotlin.math.max(0.08f, horizontal * 0.12f + 0.04f)",
    "val limit = jp.example.greenreader.precision.PrecisionMarkerGeometry.maxVerticalDifference(horizontal)",
    "anchored height limit")

s=one(s,
'''    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null''',
'''    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null
    private var precisionReferenceDistanceMeters: Float? = null
    private lateinit var precisionMarkerGeometryLabel: TextView''',
"marker UI fields")

# Reference lengths apply only to one putt; preserve saved field records.
s=one(s,
'''        precisionPuttId += 1
        precisionScanIndex = 0''',
'''        precisionPuttId += 1
        precisionReferenceDistanceMeters = null
        precisionScanIndex = 0''',"reset reference for next putt")

# In the field menu put retap controls near the existing session menu.
row_anchor='''        expandedMenu.addView(row6)
'''
row_insert='''        expandedMenu.addView(row6)

        precisionMarkerGeometryLabel = TextView(this).apply {
            setTextColor(Color.rgb(171, 255, 226))
            textSize = 11f
            setPadding(dp(7), dp(6), dp(7), dp(6))
        }
        expandedMenu.addView(precisionMarkerGeometryLabel)
        val markerRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        markerRow.addView(
            button("ボール再指定") { redoPrecisionMarkers(false) },
            LinearLayout.LayoutParams(0, dp(42), 1f)
        )
        markerRow.addView(
            button("カップ再指定") { redoPrecisionMarkers(true) },
            LinearLayout.LayoutParams(0, dp(42), 1f)
        )
        markerRow.addView(
            button("実測距離") { askPrecisionReferenceDistance() },
            LinearLayout.LayoutParams(0, dp(42), 1f)
        )
        expandedMenu.addView(markerRow)
        updatePrecisionMarkerGeometryLabel()
'''
s=one(s,row_anchor,row_insert,"marker menu controls")

helpers='''    private fun precisionMarkerGeometry():
        jp.example.greenreader.precision.PrecisionMarkerGeometry.Result? {
        val bt = ballAnchor?.pose?.translation ?: return null
        val ct = cupAnchor?.pose?.translation ?: return null
        return jp.example.greenreader.precision.PrecisionMarkerGeometry.evaluate(
            Vec3(bt[0], bt[1], bt[2]),
            Vec3(ct[0], ct[1], ct[2]),
            precisionReferenceDistanceMeters
        )
    }

    private fun precisionMarkGeometryText(): String {
        val v = precisionMarkerGeometry() ?: return "AR距離 --  /  ボールとカップを設定"
        val distance = String.format(java.util.Locale.US, "%.2f", v.horizontalMeters)
        val deltaCm = String.format(java.util.Locale.US, "%+.1f", v.verticalMeters * 100f)
        val ref = v.referenceDistanceMeters?.let {
            "  実測=" + String.format(java.util.Locale.US, "%.2f", it) + "m" +
            "  差=" + String.format(java.util.Locale.US, "%+.1f", (v.referenceErrorMeters ?: 0f) * 100f) + "cm"
        } ?: ""
        return "AR距離=" + distance + "m  高低差=" + deltaCm + "cm" + ref +
            (if (v.needsReview) "  ⚠位置を再確認" else "  （AR推定値）")
    }

    private fun updatePrecisionMarkerGeometryLabel() {
        if (::precisionMarkerGeometryLabel.isInitialized) {
            precisionMarkerGeometryLabel.text = precisionMarkGeometryText()
        }
    }

    private fun redoPrecisionMarkers(onlyCup: Boolean) {
        if (scanning) {
            Toast.makeText(this, "スキャン終了後に位置を再指定してください", Toast.LENGTH_SHORT).show()
            return
        }
        pendingMark = null
        cupAnchor?.detach()
        cupAnchor = null
        cup = null
        if (!onlyCup || ballAnchor == null) {
            ballAnchor?.detach()
            ballAnchor = null
            ball = null
            markMode = 1
        } else markMode = 2
        // Do not clear the session or saved putt records.
        precisionCurrentQuality = null
        precisionLastScanFailed = false
        precisionSurface = null
        consensusReport = null
        mapView.report = null
        overlayView.clear()
        showCamera()
        updatePrecisionRecordLabel()
        updatePrecisionMarkerGeometryLabel()
        status.text = if (markMode == 1) "ボールの中心をタップしてください"
            else "カップの中心をタップしてください"
    }

    private fun askPrecisionReferenceDistance() {
        if (scanning) return
        val input = EditText(this).apply {
            inputType = android.text.InputType.TYPE_CLASS_NUMBER or
                android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL
            hint = "例：2.00（メートル）"
            setSingleLine(true)
            precisionReferenceDistanceMeters?.let { setText(it.toString()) }
        }
        android.app.AlertDialog.Builder(this)
            .setTitle("実測距離（比較のみ・補正しません）")
            .setMessage("目印の中心間をメジャーで測った場合だけ入力します。")
            .setView(input)
            .setPositiveButton("設定") { _, _ ->
                val measured = input.text.toString().trim().toFloatOrNull()
                if (measured == null || !measured.isFinite() || measured !in 0.4f..12f) {
                    Toast.makeText(this, "0.4～12mの距離を入力してください", Toast.LENGTH_LONG).show()
                } else {
                    precisionReferenceDistanceMeters = measured
                    updatePrecisionMarkerGeometryLabel()
                    status.text = precisionMarkGeometryText()
                }
            }
            .setNeutralButton("解除") { _, _ ->
                precisionReferenceDistanceMeters = null
                updatePrecisionMarkerGeometryLabel()
            }
            .setNegativeButton("キャンセル", null)
            .show()
    }

'''
anchor="    private fun updatePrecisionRecordLabel() {"
s=one(s,anchor,helpers+anchor,"marker geometry helpers")

# Preserve the automatic ball->cup sequence. On successful cup selection,
# show actual registered anchors instead of an unexplained 'ready' state.
s=one(s,
'''            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        precisionTapTrace.append("MARK accepted target=''' ,
'''            updatePrecisionMarkerGeometryLabel()
            status.text = "位置設定完了。 " + precisionMarkGeometryText()
        }
        precisionTapTrace.append("MARK accepted target=''' ,
"registered marker feedback")

# Full geometric audit must be in a saved log for each scan and not just UI.
s=one(s,
'''        precisionLastDiagnostic =
            (precisionWindowDiagnostics + aggregateDiagnostic).joinToString(" | ")''',
'''        precisionLastDiagnostic =
            (precisionWindowDiagnostics + aggregateDiagnostic).joinToString(" | ") +
            " | MARK_GEOMETRY " + precisionMarkGeometryText()''',
"save marker geometry with scan diagnostics")

assert 'button("次のホール")' in s and 'button("結果入力")' in s
assert 'bitmap = failureBitmap' in s
assert "precisionCompletedDiagnostic = precisionLastDiagnostic" in s
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()

if "Precision 7.5" not in s: raise SystemExit("Missing 7.5 before 7.6")
s=s.replace("Precision 7.5","Precision 7.6")
g=one(g,'versionName = "7.5"','versionName = "7.6"',"versionName")
g=one(g,'versionCode = 750','versionCode = 760',"versionCode")

gate.write_text(a,encoding="utf8")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied Precision v7.6 marker geometry and independent reference check")
