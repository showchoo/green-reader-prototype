from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.3 pattern not found ({label}):\n{old[:700]}")
    s = s.replace(old, new, 1)


replace_once(
    "import android.Manifest\n",
    "import android.Manifest\nimport android.content.Intent\nimport android.net.Uri\nimport android.provider.DocumentsContract\n",
    "folder intent imports",
)

status_anchor = '''        panel.addView(status)\n\n        diagnostics = TextView(this).apply {\n'''
status_with_link = '''        panel.addView(status)\n\n        val savedDataLink = TextView(this).apply {\n            text = "保存データを開く  ›"\n            setTextColor(Color.rgb(117, 255, 167))\n            textSize = 13f\n            typeface = Typeface.DEFAULT_BOLD\n            setPadding(dp(5), 0, dp(5), dp(8))\n            isClickable = true\n            isFocusable = true\n            setOnClickListener { openSavedDataFolder() }\n        }\n        panel.addView(savedDataLink)\n\n        diagnostics = TextView(this).apply {\n'''
replace_once(status_anchor, status_with_link, "saved data link")

helper = r'''
    private fun openSavedDataFolder() {
        val target = Uri.parse(
            "content://com.android.externalstorage.documents/document/primary%3ADownload%2FGreenReaderRecords"
        )
        val downloads = Uri.parse(
            "content://com.android.externalstorage.documents/document/primary%3ADownload"
        )

        fun launch(initial: Uri) {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
                putExtra(DocumentsContract.EXTRA_INITIAL_URI, initial)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(intent)
        }

        try {
            launch(target)
        } catch (_: Throwable) {
            try {
                launch(downloads)
            } catch (_: Throwable) {
                status.text = "ファイル画面を開けませんでした。Download/GreenReaderRecords を開いてください"
            }
        }
    }

'''
replace_once(
    "    private fun toggleScan() {\n",
    helper + "    private fun toggleScan() {\n",
    "folder opener helper",
)

path.write_text(s, encoding="utf-8")
print("Applied v0.8.3 saved-data folder link")
