from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

# Insert helper before captureGlFrame, which is stable across the precision patch chain.
marker = '    private fun captureGlFrame('
if marker not in s:
    raise SystemExit("v2.2 insertion marker missing")

helper = r'''
    private fun showPrecisionFailureDialog(message: String) {
        val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
        val full = message + "\n\n" + detail

        getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
            .edit()
            .putString("last_failure", full)
            .putLong("last_failure_time", System.currentTimeMillis())
            .apply()

        status.text = message + " " + detail

        val body = TextView(this).apply {
            text = full
            setTextIsSelectable(true)
            textSize = 15f
            setPadding(40, 24, 40, 24)
        }

        android.app.AlertDialog.Builder(this)
            .setTitle("測定失敗の診断")
            .setView(body)
            .setPositiveButton("コピー") { _, _ ->
                val cm = getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                cm.setPrimaryClip(android.content.ClipData.newPlainText("Green Reader 診断", full))
                Toast.makeText(this, "診断内容をコピーしました", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("閉じる", null)
            .show()
    }

'''
s = s.replace(marker, helper + marker, 1)

targets = [
    (
        'status.text = "測定結果が揃いませんでした。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"',
        'showPrecisionFailureDialog("測定結果が揃いませんでした。もう一度スキャンしてください")'
    ),
    (
        'if (updateStatus) status.text = "測定結果が安定しませんでした。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"',
        'if (updateStatus) showPrecisionFailureDialog("測定結果が安定しませんでした。もう一度スキャンしてください")'
    ),
    (
        'if (updateStatus) status.text = "データ不足です。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"',
        'if (updateStatus) showPrecisionFailureDialog("データ不足です。もう一度スキャンしてください")'
    ),
]

changed = 0
for old, new in targets:
    if old in s:
        s = s.replace(old, new)
        changed += 1

if changed == 0:
    raise SystemExit("v2.2 failure targets missing")

s = s.replace('appVersion = "Precision 2.1"', 'appVersion = "Precision 2.2"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 210', 'versionCode = 220')
b = b.replace('versionName = "2.1"', 'versionName = "2.2"')
build.write_text(b, encoding="utf-8")

print(f"Applied Precision v2.2 persistent failure dialog ({changed} paths)")
