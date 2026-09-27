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


# Marker/anchor sanity failures take a different early-return path than slope
# failures. Route those through the same persistent/copyable diagnostic dialog.
tracking_status='''                    status.text = "位置追跡が安定しませんでした。もう一度スキャンしてください"'''
tracking_dialog='''                    showPrecisionFailureDialog("位置追跡が安定しませんでした。もう一度スキャンしてください")'''
if tracking_status in s:
    s=s.replace(tracking_status, tracking_dialog)

final_tracking='''            if (updateStatus) status.text = "位置追跡が不安定です。端末を少し動かして再試行してください"'''
final_tracking_dialog='''            if (updateStatus) showPrecisionFailureDialog("位置追跡が不安定です。端末を少し動かして再試行してください")'''
if final_tracking in s:
    s=s.replace(final_tracking, final_tracking_dialog)

p.write_text(s,encoding="utf-8")
print("Applied Precision v4.6 reliable diagnostic copy dialog")
