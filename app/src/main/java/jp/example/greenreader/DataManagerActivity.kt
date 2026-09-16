package jp.example.greenreader

import android.content.ContentUris
import android.content.ContentValues
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.MediaStore
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
import java.io.File

/** Simple manager for scan packages saved under Download/GreenReaderRecords. */
class DataManagerActivity : AppCompatActivity() {
    private lateinit var list: LinearLayout
    private lateinit var empty: TextView

    private data class ScanFolder(val name: String, val itemCount: Int)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "保存データ"
        setContentView(buildUi())
        refresh()
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
        top.addView(actionButton("ファイル画面で開く") { openSystemFolder() }, LinearLayout.LayoutParams(0, dp(44), 1f))
        top.addView(actionButton("更新") { refresh() }, LinearLayout.LayoutParams(0, dp(44), 0.55f).apply {
            marginStart = dp(8)
        })
        root.addView(top)

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
        actions.addView(actionButton("名前変更") { renameDialog(folder) }, LinearLayout.LayoutParams(0, dp(42), 1f))
        actions.addView(actionButton("削除") { confirmDelete(folder) }, LinearLayout.LayoutParams(0, dp(42), 0.7f).apply {
            marginStart = dp(8)
        })
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

    private fun loadFolders(): List<ScanFolder> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) loadModernFolders() else loadLegacyFolders()
    }

    private fun loadModernFolders(): List<ScanFolder> {
        val counts = linkedMapOf<String, Int>()
        val prefix = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/"
        val projection = arrayOf(MediaStore.Downloads.RELATIVE_PATH)
        val selection = "${MediaStore.Downloads.RELATIVE_PATH} LIKE ?"
        val args = arrayOf("$prefix%")
        contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI, projection, selection, args, null)?.use { c ->
            val relIndex = c.getColumnIndexOrThrow(MediaStore.Downloads.RELATIVE_PATH)
            while (c.moveToNext()) {
                val rel = c.getString(relIndex) ?: continue
                val rest = rel.removePrefix(prefix).trim('/')
                val folder = rest.substringBefore('/')
                if (folder.isNotBlank()) counts[folder] = (counts[folder] ?: 0) + 1
            }
        }
        return counts.entries
            .sortedByDescending { it.key }
            .map { ScanFolder(it.key, it.value) }
    }

    private fun loadLegacyFolders(): List<ScanFolder> {
        val root = File(getExternalFilesDir(null), "GreenReaderRecords")
        return root.listFiles()
            ?.filter { it.isDirectory }
            ?.sortedByDescending { it.name }
            ?.map { ScanFolder(it.name, it.listFiles()?.size ?: 0) }
            ?: emptyList()
    }

    private fun folderExists(name: String): Boolean = loadFolders().any { it.name == name }

    private fun renameFolder(oldName: String, newName: String): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            val root = File(getExternalFilesDir(null), "GreenReaderRecords")
            return File(root, oldName).renameTo(File(root, newName))
        }
        val oldRel = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/$oldName/"
        val newRel = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/$newName/"
        val ids = queryIdsForRelativePath(oldRel)
        if (ids.isEmpty()) return false
        var changed = 0
        ids.forEach { id ->
            val uri = ContentUris.withAppendedId(MediaStore.Downloads.EXTERNAL_CONTENT_URI, id)
            val values = ContentValues().apply { put(MediaStore.Downloads.RELATIVE_PATH, newRel) }
            changed += contentResolver.update(uri, values, null, null)
        }
        return changed == ids.size
    }

    private fun deleteFolder(name: String): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            val root = File(getExternalFilesDir(null), "GreenReaderRecords")
            return File(root, name).deleteRecursively()
        }
        val rel = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/$name/"
        val ids = queryIdsForRelativePath(rel)
        if (ids.isEmpty()) return false
        var deleted = 0
        ids.forEach { id ->
            val uri = ContentUris.withAppendedId(MediaStore.Downloads.EXTERNAL_CONTENT_URI, id)
            deleted += contentResolver.delete(uri, null, null)
        }
        return deleted == ids.size
    }

    private fun queryIdsForRelativePath(path: String): List<Long> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return emptyList()
        val ids = mutableListOf<Long>()
        val projection = arrayOf(MediaStore.Downloads._ID)
        val selection = "${MediaStore.Downloads.RELATIVE_PATH} = ?"
        contentResolver.query(MediaStore.Downloads.EXTERNAL_CONTENT_URI, projection, selection, arrayOf(path), null)?.use { c ->
            val idIndex = c.getColumnIndexOrThrow(MediaStore.Downloads._ID)
            while (c.moveToNext()) ids += c.getLong(idIndex)
        }
        return ids
    }

    private fun openSystemFolder() {
        val target = Uri.parse("content://com.android.externalstorage.documents/document/primary%3ADownload%2FGreenReaderRecords")
        val downloads = Uri.parse("content://com.android.externalstorage.documents/document/primary%3ADownload")
        fun launch(uri: Uri) {
            startActivity(Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
                putExtra(DocumentsContract.EXTRA_INITIAL_URI, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            })
        }
        try { launch(target) } catch (_: Throwable) {
            try { launch(downloads) } catch (_: Throwable) { toast("ファイル画面を開けませんでした") }
        }
    }

    private fun actionButton(label: String, action: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        setOnClickListener { action() }
    }

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
}
