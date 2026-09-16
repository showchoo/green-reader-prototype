package jp.example.greenreader

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.DocumentsContract
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.documentfile.provider.DocumentFile
import java.io.File

/**
 * Manages scan packages saved under Download/GreenReaderRecords.
 *
 * Android 10+ deliberately uses Storage Access Framework (DocumentFile) instead of
 * MediaStore queries. MediaStore can expose only app-owned/indexed rows on some devices,
 * which made older scan folders disappear from the list. A persisted tree permission lets
 * us enumerate the real directory contents and therefore manage old and new scans equally.
 */
class DataManagerActivity : AppCompatActivity() {
    companion object {
        private const val REQ_RECORDS_TREE = 9201
        private const val PREFS = "saved_data_manager"
        private const val KEY_RECORDS_TREE_URI = "records_tree_uri"
        private const val RECORDS_FOLDER = "GreenReaderRecords"
    }

    private lateinit var list: LinearLayout
    private lateinit var empty: TextView
    private var autoPickerShown = false

    private data class ScanFolder(val name: String, val itemCount: Int)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "保存データ"
        setContentView(buildUi())
        refresh()

        // v0.8.6 migration: ask once for direct access to the real saved-data folder.
        if (usesSharedDownloadFolder() && recordsRoot() == null && !autoPickerShown) {
            autoPickerShown = true
            list.post { requestRecordsFolderAccess() }
        }
    }

    override fun onResume() {
        super.onResume()
        if (::list.isInitialized) refresh()
    }

    private fun buildUi(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            setBackgroundColor(Color.rgb(6, 17, 12))
        }

        root.addView(TextView(this).apply {
            text = "保存データ"
            setTextColor(Color.WHITE)
            textSize = 24f
            typeface = Typeface.DEFAULT_BOLD
        })
        root.addView(TextView(this).apply {
            text = "Download/GreenReaderRecords"
            setTextColor(Color.rgb(151, 191, 164))
            textSize = 13f
            setPadding(0, dp(2), 0, dp(12))
        })

        val top = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        top.addView(
            actionButton("保存フォルダを開く") { requestRecordsFolderAccess() },
            LinearLayout.LayoutParams(0, dp(44), 1f)
        )
        top.addView(
            actionButton("更新") { refresh() },
            LinearLayout.LayoutParams(0, dp(44), 0.48f).apply { marginStart = dp(8) }
        )
        root.addView(top)

        root.addView(actionButton("全データ削除") { confirmDeleteAll() }.apply {
            setTextColor(Color.rgb(190, 35, 35))
        }, LinearLayout.LayoutParams(-1, dp(44)).apply { topMargin = dp(8) })

        empty = TextView(this).apply {
            text = "保存データはまだありません"
            setTextColor(Color.LTGRAY)
            textSize = 15f
            gravity = Gravity.CENTER
            setPadding(0, dp(34), 0, dp(34))
        }
        root.addView(empty)

        list = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(8), 0, dp(24))
        }
        val scroll = ScrollView(this).apply { addView(list) }
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        return root
    }

    private fun refresh() {
        val folders = loadFolders()
        list.removeAllViews()

        if (usesSharedDownloadFolder() && recordsRoot() == null) {
            empty.text = "最初に「保存フォルダを開く」を押し、\nGreenReaderRecords を選んで「このフォルダを使用」を押してください"
            empty.visibility = View.VISIBLE
            return
        }

        empty.text = "保存データはまだありません"
        empty.visibility = if (folders.isEmpty()) View.VISIBLE else View.GONE
        folders.forEach { folder -> list.addView(folderRow(folder)) }
    }

    private fun folderRow(folder: ScanFolder): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(12), dp(12), dp(12))
            setBackgroundColor(Color.rgb(17, 37, 27))
        }
        box.addView(TextView(this).apply {
            text = folder.name
            setTextColor(Color.WHITE)
            textSize = 16f
            typeface = Typeface.DEFAULT_BOLD
        })
        box.addView(TextView(this).apply {
            text = "${folder.itemCount} ファイル"
            setTextColor(Color.rgb(154, 190, 165))
            textSize = 12f
            setPadding(0, dp(2), 0, dp(8))
        })

        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        actions.addView(
            actionButton("名前変更") { renameDialog(folder) },
            LinearLayout.LayoutParams(0, dp(42), 1f)
        )
        actions.addView(
            actionButton("削除") { confirmDelete(folder) },
            LinearLayout.LayoutParams(0, dp(42), 0.7f).apply { marginStart = dp(8) }
        )
        box.addView(actions)

        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(box, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
        }
    }

    private fun renameDialog(folder: ScanFolder) {
        val input = EditText(this).apply {
            setText(folder.name)
            setSelection(text.length)
            setSingleLine(true)
        }
        AlertDialog.Builder(this)
            .setTitle("名前を変更")
            .setView(input)
            .setNegativeButton("キャンセル", null)
            .setPositiveButton("変更") { _, _ ->
                val newName = input.text.toString().trim()
                when {
                    newName.isBlank() -> toast("名前を入力してください")
                    newName.contains('/') || newName.contains('\\') -> toast("/ と \\ は使えません")
                    newName == folder.name -> Unit
                    folderExists(newName) -> toast("同じ名前のデータがあります")
                    renameFolder(folder.name, newName) -> {
                        toast("名前を変更しました")
                        refresh()
                    }
                    else -> toast("名前を変更できませんでした")
                }
            }
            .show()
    }

    private fun confirmDelete(folder: ScanFolder) {
        AlertDialog.Builder(this)
            .setTitle("削除しますか？")
            .setMessage("${folder.name}\n\nこのスキャンの画像・Depth点群・解析データをすべて削除します。")
            .setNegativeButton("キャンセル", null)
            .setPositiveButton("削除") { _, _ ->
                if (deleteFolder(folder.name)) {
                    toast("削除しました")
                    refresh()
                } else {
                    toast("削除できませんでした")
                }
            }
            .show()
    }

    private fun confirmDeleteAll() {
        val folders = loadFolders()
        if (usesSharedDownloadFolder() && recordsRoot() == null) {
            toast("先に保存フォルダへのアクセスを許可してください")
            requestRecordsFolderAccess()
            return
        }
        if (folders.isEmpty()) {
            toast("削除するデータがありません")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("全データを削除しますか？")
            .setMessage("保存されている ${folders.size} 件のスキャンデータをすべて削除します。\n\nこの操作は元に戻せません。")
            .setNegativeButton("キャンセル", null)
            .setPositiveButton("全削除") { _, _ ->
                if (deleteAllFolders()) {
                    toast("全データを削除しました")
                    refresh()
                } else {
                    toast("一部のデータを削除できませんでした")
                    refresh()
                }
            }
            .show()
    }

    private fun usesSharedDownloadFolder(): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q

    private fun loadFolders(): List<ScanFolder> =
        if (usesSharedDownloadFolder()) loadDocumentFolders() else loadLegacyFolders()

    private fun loadDocumentFolders(): List<ScanFolder> {
        val root = recordsRoot() ?: return emptyList()
        return safeChildren(root)
            .filter { it.isDirectory }
            .mapNotNull { folder ->
                val name = folder.name ?: return@mapNotNull null
                ScanFolder(name, safeChildren(folder).size)
            }
            .sortedByDescending { it.name }
    }

    private fun loadLegacyFolders(): List<ScanFolder> {
        val root = File(getExternalFilesDir(null), RECORDS_FOLDER)
        return root.listFiles()
            ?.filter { it.isDirectory }
            ?.sortedByDescending { it.name }
            ?.map { ScanFolder(it.name, it.listFiles()?.size ?: 0) }
            ?: emptyList()
    }

    private fun folderExists(name: String): Boolean {
        if (!usesSharedDownloadFolder()) {
            return File(File(getExternalFilesDir(null), RECORDS_FOLDER), name).exists()
        }
        val root = recordsRoot() ?: return false
        return safeChildren(root).any { it.name == name }
    }

    private fun renameFolder(oldName: String, newName: String): Boolean {
        if (!usesSharedDownloadFolder()) {
            val root = File(getExternalFilesDir(null), RECORDS_FOLDER)
            return File(root, oldName).renameTo(File(root, newName))
        }
        val root = recordsRoot() ?: return false
        val target = safeChildren(root).firstOrNull { it.isDirectory && it.name == oldName }
            ?: return false
        return try {
            target.renameTo(newName)
        } catch (_: Throwable) {
            false
        }
    }

    private fun deleteFolder(name: String): Boolean {
        if (!usesSharedDownloadFolder()) {
            val root = File(getExternalFilesDir(null), RECORDS_FOLDER)
            return File(root, name).deleteRecursively()
        }
        val root = recordsRoot() ?: return false
        val target = safeChildren(root).firstOrNull { it.isDirectory && it.name == name }
            ?: return false
        return try {
            target.delete()
        } catch (_: Throwable) {
            false
        }
    }

    private fun deleteAllFolders(): Boolean {
        if (!usesSharedDownloadFolder()) {
            val root = File(getExternalFilesDir(null), RECORDS_FOLDER)
            if (!root.exists()) return true
            var ok = true
            root.listFiles()?.forEach { child -> if (!child.deleteRecursively()) ok = false }
            return ok
        }

        val root = recordsRoot() ?: return false
        var ok = true
        safeChildren(root).forEach { child ->
            val deleted = try { child.delete() } catch (_: Throwable) { false }
            if (!deleted) ok = false
        }
        return ok
    }

    /** Returns the persisted, real GreenReaderRecords directory. No MediaStore indexing involved. */
    private fun recordsRoot(): DocumentFile? {
        if (!usesSharedDownloadFolder()) return null
        val uriText = getSharedPreferences(PREFS, MODE_PRIVATE)
            .getString(KEY_RECORDS_TREE_URI, null)
            ?: return null
        return try {
            val uri = Uri.parse(uriText)
            DocumentFile.fromTreeUri(this, uri)
                ?.takeIf { it.exists() && it.isDirectory && it.canRead() }
        } catch (_: Throwable) {
            null
        }
    }

    private fun safeChildren(folder: DocumentFile): List<DocumentFile> =
        try { folder.listFiles().toList() } catch (_: Throwable) { emptyList() }

    private fun requestRecordsFolderAccess() {
        if (!usesSharedDownloadFolder()) return

        val saved = getSharedPreferences(PREFS, MODE_PRIVATE)
            .getString(KEY_RECORDS_TREE_URI, null)
            ?.let(Uri::parse)
        val target = saved ?: Uri.parse(
            "content://com.android.externalstorage.documents/document/primary%3ADownload%2FGreenReaderRecords"
        )

        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
            putExtra(DocumentsContract.EXTRA_INITIAL_URI, target)
            addFlags(
                Intent.FLAG_GRANT_READ_URI_PERMISSION or
                    Intent.FLAG_GRANT_WRITE_URI_PERMISSION or
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION or
                    Intent.FLAG_GRANT_PREFIX_URI_PERMISSION
            )
        }
        try {
            startActivityForResult(intent, REQ_RECORDS_TREE)
        } catch (_: Throwable) {
            toast("フォルダ選択画面を開けませんでした")
        }
    }

    @Deprecated("Deprecated in Android")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_RECORDS_TREE || resultCode != RESULT_OK) return

        val uri = data?.data ?: return
        val chosen = try { DocumentFile.fromTreeUri(this, uri) } catch (_: Throwable) { null }
        val treeId = try { DocumentsContract.getTreeDocumentId(uri) } catch (_: Throwable) { null }
        val correctFolder = chosen?.name == RECORDS_FOLDER ||
            treeId?.substringAfterLast('/') == RECORDS_FOLDER

        if (!correctFolder) {
            toast("GreenReaderRecords フォルダを選択してください")
            return
        }

        val takeFlags = data.flags and
            (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        try {
            contentResolver.takePersistableUriPermission(uri, takeFlags)
        } catch (_: Throwable) {
            toast("フォルダへのアクセスを保存できませんでした")
            return
        }

        getSharedPreferences(PREFS, MODE_PRIVATE)
            .edit()
            .putString(KEY_RECORDS_TREE_URI, uri.toString())
            .apply()

        toast("保存フォルダを読み込みました")
        refresh()
    }

    private fun actionButton(label: String, action: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        setOnClickListener { action() }
    }

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}
