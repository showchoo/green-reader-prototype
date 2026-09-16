from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")

old = '''    private fun openSavedDataFolder() {
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
new = '''    private fun openSavedDataFolder() {
        try {
            startActivity(Intent(this, DataManagerActivity::class.java))
        } catch (_: Throwable) {
            status.text = "保存データ画面を開けませんでした"
        }
    }
'''
if old not in s:
    raise SystemExit("v0.8.4 saved data opener pattern not found")
s = s.replace(old, new, 1)
path.write_text(s, encoding="utf-8")
print("Applied v0.8.4 in-app saved data manager")
