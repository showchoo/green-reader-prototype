"""v6.2: field-test UX — keep scan failures non-blocking and diagnostics manually copyable."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.2 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

# Add a persistent/manual diagnostic copy button beside 3D view.
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

# Add non-blocking recorder/manual copy helpers before the existing failure dialog.
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
        val savedFailure = prefs.getString("last_failure", null)
        val current = if (precisionLastDiagnostic.isBlank()) null else "測定データ\n\n" + precisionLastDiagnostic
        val full = current ?: savedFailure
        if (full.isNullOrBlank()) {
            Toast.makeText(this, "コピーできる診断データはまだありません", Toast.LENGTH_SHORT).show()
            return
        }
        copyPrecisionDiagnostic(full)
    }

'''
s=s[:idx]+helper+s[idx:]

replacements = {
    'showPrecisionFailureDialog("位置追跡が安定しませんでした。もう一度スキャンしてください")':
        'recordPrecisionScanFailure("位置追跡が安定しませんでした。もう一度スキャンしてください")',
    'showPrecisionFailureDialog("測定結果が揃いませんでした。もう一度スキャンしてください")':
        'recordPrecisionScanFailure("測定結果が揃いませんでした。もう一度スキャンしてください")',
    'showPrecisionFailureDialog("位置追跡が不安定です。端末を少し動かして再試行してください")':
        'recordPrecisionScanFailure("位置追跡が不安定です。端末を少し動かして再試行してください")',
    'showPrecisionFailureDialog("測定結果が安定しませんでした。もう一度スキャンしてください")':
        'recordPrecisionScanFailure("測定結果が安定しませんでした。もう一度スキャンしてください")',
}
for old,new in replacements.items():
    if old not in s:
        raise SystemExit("v6.2 scan failure call missing: "+old)
    s=s.replace(old,new)

# Keep marker acquisition failures modal: they require immediate user correction.
assert 'showPrecisionFailureDialog("カップ位置を取得できませんでした。もう一度カップをタップしてください")' in s
assert 'showPrecisionFailureDialog("ボール位置を取得できませんでした。もう一度タップしてください")' in s

if s.count('appVersion = "Precision 6.1"') != 1:
    raise SystemExit("v6.2 app version target missing")
s=s.replace('appVersion = "Precision 6.1"','appVersion = "Precision 6.2"',1)

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.1"') != 1 or g.count('versionCode = 610') != 1:
    raise SystemExit("v6.2 gradle version target missing")
g=g.replace('versionName = "6.1"','versionName = "6.2"',1)
g=g.replace('versionCode = 610','versionCode = 620',1)

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.2 non-blocking scan failure UX")
