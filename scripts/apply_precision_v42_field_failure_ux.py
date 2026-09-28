"""v6.2: field-test UX — no automatic diagnostic dialogs; manual copy stays available."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.2 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

# Manual diagnostic copy button.
once(
'''        val row4 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        view3dToggleButton = button("3D目線") { if (view3d.visibility == View.VISIBLE) showCamera() else show3D() }
        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(row4)
''',
'''        val row4 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        view3dToggleButton = button("3D目線") { if (view3d.visibility == View.VISIBLE) showCamera() else show3D() }
        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, -2, 1f))
        row4.addView(button("診断コピー") { copyLastPrecisionDiagnostic() }, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(row4)
''',
"diagnostic copy button"
)

marker='    private fun showPrecisionFailureDialog(message: String) {'
idx=s.index(marker)
helper=r'''    private fun recordPrecisionScanFailure(message: String) {
        val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
        val full = message + "\n\n" + detail
        getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
            .edit()
            .putString("last_failure", full)
            .putLong("last_failure_time", System.currentTimeMillis())
            .apply()
        status.text = message + "（診断保存済み）"
        Toast.makeText(this, "再スキャンできます", Toast.LENGTH_SHORT).show()
    }

    private fun copyLastPrecisionDiagnostic() {
        val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
        val current = if (precisionLastDiagnostic.isBlank()) null else "測定データ\n\n" + precisionLastDiagnostic
        val savedFailure = prefs.getString("last_failure", null)
        val savedMarker = prefs.getString("last_marker", null)
        val full = current ?: savedFailure ?: savedMarker
        if (full.isNullOrBlank()) {
            Toast.makeText(this, "コピーできる診断データはまだありません", Toast.LENGTH_SHORT).show()
            return
        }
        copyPrecisionDiagnostic(full)
    }

'''
s=s[:idx]+helper+s[idx:]

# Scan/analyze failures become non-modal.
for msg in (
    "位置追跡が安定しませんでした。もう一度スキャンしてください",
    "測定結果が揃いませんでした。もう一度スキャンしてください",
    "位置追跡が不安定です。端末を少し動かして再試行してください",
    "測定結果が安定しませんでした。もう一度スキャンしてください",
):
    old=f'showPrecisionFailureDialog("{msg}")'
    new=f'recordPrecisionScanFailure("{msg}")'
    if old not in s:
        raise SystemExit("v6.2 scan failure call missing: "+msg)
    s=s.replace(old,new)

# Marker diagnostics are always retained, but no copy dialog pops up after
# successful Cup placement or failed marker acquisition.
start=s.index("    private fun finishPrecisionTap(mode: Int, accepted: Boolean) {")
end=s.index("\n    private fun ", start+20)
marker_fn=r'''    private fun finishPrecisionTap(mode: Int, accepted: Boolean) {
        val trace = precisionTapTrace.toString()
        if (mode == 1) precisionBallTapDiagnostic = trace
        precisionLastDiagnostic = if (mode == 2) precisionBallTapDiagnostic + "\n" + trace else trace
        getSharedPreferences("precision_diagnostics", MODE_PRIVATE).edit()
            .putString("last_marker", precisionLastDiagnostic).apply()
        // Field mode: never block the next action with a diagnostic dialog.
        // The same trace remains available from the manual 診断コピー button.
    }
'''
s=s[:start]+marker_fn+s[end:]

# Successful five-window scans should continue directly into result generation;
# diagnostics stay available manually instead of opening a modal copy screen.
success_start='''        runOnUiThread {
            status.text = "複数回の測定結果を照合しました。高精度解析中…"
            val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
            val full = "測定データ\n\n" + detail
            val body = TextView(this).apply {
                text = full
                setTextIsSelectable(true)
                textSize = 15f
                setPadding(40, 24, 40, 24)
            }
            val scroll = android.widget.ScrollView(this).apply {
                isFillViewport = true
                addView(body)
            }
            val dialog = android.app.AlertDialog.Builder(this)
                .setTitle("測定データ")
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
        }'''
success_new='''        runOnUiThread {
            status.text = "複数回の測定結果を照合しました。高精度解析中…"
        }'''
once(success_start,success_new,"successful scan diagnostic dialog")

if s.count('appVersion = "Precision 6.1"') != 1:
    raise SystemExit("v6.2 app version target missing")
s=s.replace('appVersion = "Precision 6.1"','appVersion = "Precision 6.2"',1)

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.1"') != 1 or g.count('versionCode = 610') != 1:
    raise SystemExit("v6.2 gradle version target missing")
g=g.replace('versionName = "6.1"','versionName = "6.2"',1)
g=g.replace('versionCode = 610','versionCode = 620',1)

assert 'button("診断コピー") { copyLastPrecisionDiagnostic() }' in s
assert 'private fun finishPrecisionTap' in s
assert '.setTitle(if (accepted)' not in s
assert '.setTitle("測定データ")' not in s

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.2 field-test UX: manual diagnostics, no automatic copy dialogs")
