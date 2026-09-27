from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

start=s.find("    private fun showPrecisionFailureDialog(message: String) {")
end=s.find("    private fun captureGlFrame(", start)
if start < 0 or end < 0:
    raise SystemExit("v4.6 target missing: failure dialog")

new_helper=r'''    private fun copyPrecisionDiagnostic(full: String) {
        val cm = getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        val clip = android.content.ClipData.newPlainText("Green Reader 診断", full)
        cm.setPrimaryClip(clip)
        Toast.makeText(this, "診断内容をコピーしました", Toast.LENGTH_SHORT).show()
    }

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
        val scroll = android.widget.ScrollView(this).apply {
            isFillViewport = true
            addView(body)
        }

        val dialog = android.app.AlertDialog.Builder(this)
            .setTitle("測定失敗の診断")
            .setView(scroll)
            .setPositiveButton("コピー", null)
            .setNegativeButton("閉じる", null)
            .create()

        dialog.setOnShowListener {
            // Do not let the platform auto-dismiss before Clipboard finishes.
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                copyPrecisionDiagnostic(full)
            }
        }
        dialog.show()
    }

'''
s=s[:start]+new_helper+s[end:]
p.write_text(s,encoding="utf-8")
print("Applied Precision v4.6 reliable diagnostic copy dialog")
