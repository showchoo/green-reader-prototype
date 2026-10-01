"""Repair the v32 state regression and expose single-tap acquisition diagnostics.

Apply after v34. Thresholds, candidate priority and slope fitting are unchanged.
"""
from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")


def once(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit(f"v5.5 marker pipeline expected exactly one target: {old[:160]}")
    s = s.replace(old, new, 1)


def replace_function(name, replacement):
    global s
    start = s.index(f"    private fun {name}(")
    end = s.index("\n    private fun ", start + 20)
    s = s[:start] + replacement.rstrip() + "\n" + s[end:]


once('    private var markMode = 0\n', '''    private var precisionTapTrace = StringBuilder()
    private var precisionBallTapDiagnostic = ""
    private var markMode = 0
''')

replace_function("markAt", r'''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return
        val target = if (mode == 1) "ball" else "cup"
        precisionTapTrace = StringBuilder("Precision 5.5 TAP $target received x=$x y=$y mode=$mode\n")
        val f = latestFrame
        precisionTapTrace.append("latestFrame available=${f != null} viewport=${viewportW}x${viewportH}\n")
        if (f == null || f.camera.trackingState != TrackingState.TRACKING) {
            precisionTapTrace.append("camera tracking=${f?.camera?.trackingState} reason=${f?.camera?.trackingFailureReason}\n")
            status.text = "ARの準備中です。端末を少し動かしてからもう一度タップしてください"
            finishPrecisionTap(mode, false)
            return
        }
        precisionTapTrace.append("camera tracking=${f.camera.trackingState} timestamp=${f.timestamp}\n")
        var p = resolveMarkPoint(f, x, y)
        if (p == null) {
            p = tracedMarkCandidate(f, "neighborDepth") { ballPointFromNeighborDepth(f, x, y) }
            if (p != null) precisionTapTrace.append("selected source=neighborDepth\n")
        } else {
            precisionTapTrace.append("neighborDepth=not-needed\n")
        }
        if (p != null) {
            applyMark(mode, p)
            return
        }
        pendingMark = null
        markMode = mode
        precisionTapTrace.append("MARK tap-unresolved target=$target\n")
        status.text = if (mode == 1) "ボール位置を取得できませんでした。もう一度タップしてください"
            else "カップ位置を取得できませんでした。もう一度タップしてください"
        finishPrecisionTap(mode, false)
    }
''')

# v32 replaced applyMark wholesale and erased v082's automatic transition.
once('''        markMode = 0
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
''', '''        collector.clear()
        if (mode == 1) {
            ballAnchor?.detach()
            ballAnchor = newAnchor
            ball = p
            markMode = 2
            status.text = "次にカップをタップしてください"
        } else {
            cupAnchor?.detach()
            cupAnchor = newAnchor
            cup = p
            markMode = 0
            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        precisionTapTrace.append("MARK accepted target=${if (mode == 1) "ball" else "cup"} nextMode=$markMode\\n")
        finishPrecisionTap(mode, true)
        if (testMode) updateDiagnostics()
''')

once('''        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (_: Throwable) {
            null
        }
''', '''        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (e: Exception) {
            precisionTapTrace.append("anchor error=${e.javaClass.simpleName}: ${e.message}\\n")
            null
        }
        precisionTapTrace.append("anchor created=${newAnchor != null} tracking=${newAnchor?.trackingState} world=${newAnchor?.pose?.translation?.contentToString()}\\n")
''')
once('''            status.text = "位置を固定できませんでした。端末を少し動かしてもう一度タップしてください"
            return
''', '''            status.text = "位置を固定できませんでした。端末を少し動かしてもう一度タップしてください"
            finishPrecisionTap(mode, false)
            return
''')
once('''                    showPrecisionFailureDialog("カップ位置を取得できませんでした。もう一度カップをタップしてください")
''', '''                    precisionTapTrace.append(precisionLastDiagnostic).append("\\n")
                    finishPrecisionTap(mode, false)
''')

replace_function("resolveMarkPoint", r'''    private fun resolveMarkPoint(frame: Frame, x: Float, y: Float): Vec3? {
        val exact = tracedMarkCandidate(frame, "exactSurface") { exactSurfaceHitPoint(frame, x, y) }
        if (exact != null) {
            precisionTapTrace.append("selected source=exactSurface\nnearbySurface=not-needed\nexactDepth=not-needed\n")
            return exact
        }
        val nearby = tracedMarkCandidate(frame, "nearbySurface") { tinyNearbyHitPoint(frame, x, y) }
        if (nearby != null) {
            precisionTapTrace.append("selected source=nearbySurface\nexactDepth=not-needed\n")
            return nearby
        }
        val depth = tracedMarkCandidate(frame, "exactDepth") { depthPointAtTap(frame, x, y) }
        if (depth != null) precisionTapTrace.append("selected source=exactDepth\n")
        return depth
    }

    private fun tracedMarkCandidate(frame: Frame, source: String, acquire: () -> Vec3?): Vec3? {
        val p = try { acquire() } catch (e: Exception) {
            precisionTapTrace.append("$source error=${e.javaClass.simpleName}: ${e.message}\n")
            null
        }
        if (p == null) {
            precisionTapTrace.append("$source=null\n")
            return null
        }
        val c = frame.camera.pose.translation
        val dx = p.x - c[0]
        val dy = p.y - c[1]
        val dz = p.z - c[2]
        val d2 = dx * dx + dy * dy + dz * dz
        val accepted = d2.isFinite() && d2 in 0.04f..16.0f
        precisionTapTrace.append("$source world=(${p.x},${p.y},${p.z}) cameraDistance=${kotlin.math.sqrt(d2)} accepted=$accepted\n")
        return if (accepted) p else null
    }

    private fun finishPrecisionTap(mode: Int, accepted: Boolean) {
        val trace = precisionTapTrace.toString()
        if (mode == 1) precisionBallTapDiagnostic = trace
        precisionLastDiagnostic = if (mode == 2) precisionBallTapDiagnostic + "\n" + trace else trace
        getSharedPreferences("precision_diagnostics", MODE_PRIVATE).edit()
            .putString("last_marker", precisionLastDiagnostic).apply()
        // A normal Ball tap immediately advances to Cup. Cup attempts always
        // expose both traces; failed Ball attempts expose their own trace too.
        if (mode != 2 && accepted) return
        val full = status.text.toString() + "\n\n" + precisionLastDiagnostic
        val body = TextView(this).apply {
            text = full
            setTextIsSelectable(true)
            textSize = 14f
            setPadding(32, 20, 32, 20)
        }
        val scroll = android.widget.ScrollView(this).apply { addView(body) }
        val dialog = android.app.AlertDialog.Builder(this)
            .setTitle(if (accepted) "位置設定完了・診断" else "位置取得の診断")
            .setView(scroll)
            .setPositiveButton("コピー", null)
            .setNegativeButton("閉じる", null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                copyPrecisionDiagnostic(full)
            }
        }
        dialog.show()
    }
''')

# The two Depth helpers previously swallowed API exceptions without any evidence.
for name in ("depthPointAtTap", "ballPointFromNeighborDepth"):
    start = s.index(f"    private fun {name}(")
    end = s.index("\n    private fun ", start + 20)
    fn = s[start:end]
    old = '''        } catch (_: NotYetAvailableException) {
            null
        } catch (_: Throwable) {
            null
        }
'''
    new = f'''        }} catch (e: Exception) {{
            precisionTapTrace.append("{name} error=${{e.javaClass.simpleName}}: ${{e.message}}\\n")
            null
        }}
'''
    if fn.count(old) != 1:
        raise SystemExit(f"v5.5 missing exception block: {name}")
    s = s[:start] + fn.replace(old, new, 1) + s[end:]

p.write_text(s, encoding="utf-8")
print("Applied Precision v5.5 Ball-to-Cup transition repair and tap diagnostics")
