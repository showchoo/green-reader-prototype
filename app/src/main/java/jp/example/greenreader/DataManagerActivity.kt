package jp.example.greenreader

import android.app.RecoverableSecurityException
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
    companion object {
        private const val REQ_DELETE_ONE = 9101
        private const val REQ_WRITE = 9102
        private const val REQ_DELETE_ALL = 9103
    }

    private lateinit var list: LinearLayout
    private lateinit var empty: TextView
    private var pendingRenameOld: String? = null
    private var pendingRenameNew: String? = null

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
                    renameFolder(folder.name, newName) -> Unit
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
            .setPositiveButton("削除") { _, _ -> deleteFolder(folder.name) }
            .show()
    }

    private fun confirmDeleteAll() {
        val folders = loadFolders()
        if (folders.isEmpty()) {
            toast("削除するデータがありません")
            return
        }
        AlertDialog.Builder(this)
            .setTitle("全データを削除しますか？")
            .setMessage("保存されている ${folders.size} 件のスキャンデータをすべて削除します。\n\nこの操作は元に戻せません。")
            .setNegativeButton("キャンセル", null)
            .setPositiveButton("全削除") { _, _ -> deleteAllFolders() }
            .show()
    }

    private fun loadFolders(): List<ScanFolder> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) loadModernFolders() else loadLegacyFolders()

    private fun loadModernFolders(): List<ScanFolder> {
        val counts = linkedMapOf<String, Int>()
        val prefix = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/"
        val projection = arrayOf(MediaStore.Downloads.RELATIVE_PATH)
        val selection = "${MediaStore.Downloads.RELATIVE_PATH} LIKE ?"
        contentResolver.query(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            projection,
            selection,
            arrayOf("$prefix%"),
            null
        )?.use { c ->
            val relIndex = c.getColumnIndexOrThrow(MediaStore.Downloads.RELATIVE_PATH)
            while (c.moveToNext()) {
                val rel = c.getString(relIndex) ?: continue
                val rest = rel.removePrefix(prefix).trim('/')
                val folder = rest.substringBefore('/')
                if (folder.isNotBlank()) counts[folder] = (counts[folder] ?: 0) + 1
            }
        }
        return counts.entries.sortedByDescending { it.key }.map { ScanFolder(it.key, it.value) }
    }

    private fun loadLegacyFolders(): List<ScanFolder> {
        val root = File(getExternalFilesDir(null), "GreenReaderRecords")
        return root.listFiles()?.filter { it.isDirectory }?.sortedByDescending { it.name }
            ?.map { ScanFolder(it.name, it.listFiles()?.size ?: 0) } ?: emptyList()
    }

    private fun folderExists(name: String): Boolean = loadFolders().any { it.name == name }

    private fun renameFolder(oldName: String, newName: String): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            val root = File(getExternalFilesDir(null), "GreenReaderRecords")
            val ok = File(root, oldName).renameTo(File(root, newName))
            if (ok) { toast("名前を変更しました"); refresh() }
            return ok
        }
        val oldRel = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/$oldName/"
        val newRel = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/$newName/"
        val uris = queryUrisForRelativePath(oldRel)
        if (uris.isEmpty()) return false
        return try {
            var changed = 0
            uris.forEach { uri ->
                changed += contentResolver.update(
                    uri,
                    ContentValues().apply { put(MediaStore.Downloads.RELATIVE_PATH, newRel) },
                    null,
                    null
                )
            }
            val ok = changed == uris.size
            if (ok) { toast("名前を変更しました"); refresh() }
            ok
        } catch (e: SecurityException) {
            requestRenamePermission(oldName, newName, uris, e)
        }
    }

    private fun requestRenamePermission(oldName: String, newName: String, uris: List<Uri>, error: SecurityException): Boolean {
        pendingRenameOld = oldName
        pendingRenameNew = newName
        return try {
            when {
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.R -> {
                    val request = MediaStore.createWriteRequest(contentResolver, uris)
                    startIntentSenderForResult(request.intentSender, REQ_WRITE, null, 0, 0, 0)
                    true
                }
                Build.VERSION.SDK_INT == Build.VERSION_CODES.Q && error is RecoverableSecurityException -> {
                    startIntentSenderForResult(error.userAction.actionIntent.intentSender, REQ_WRITE, null, 0, 0, 0)
                    true
                }
                else -> false
            }
        } catch (_: Throwable) {
            false
        }
    }

    private fun deleteFolder(name: String) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            val root = File(getExternalFilesDir(null), "GreenReaderRecords")
            if (File(root, name).deleteRecursively()) {
                toast("削除しました")
                refresh()
            } else toast("削除できませんでした")
            return
        }
        val rel = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/$name/"
        val uris = queryUrisForRelativePath(rel)
        if (uris.isEmpty()) {
            toast("削除できませんでした")
            return
        }
        requestDelete(uris, REQ_DELETE_ONE)
    }

    private fun deleteAllFolders() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            val root = File(getExternalFilesDir(null), "GreenReaderRecords")
            val ok = !root.exists() || root.deleteRecursively()
            if (ok) {
                toast("全データを削除しました")
                refresh()
            } else toast("削除できませんでした")
            return
        }
        val uris = queryAllRecordUris()
        if (uris.isEmpty()) {
            toast("削除するデータがありません")
            return
        }
        requestDelete(uris, REQ_DELETE_ALL)
    }

    private fun requestDelete(uris: List<Uri>, requestCode: Int) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val request = MediaStore.createDeleteRequest(contentResolver, uris)
                startIntentSenderForResult(request.intentSender, requestCode, null, 0, 0, 0)
                return
            }
            var deleted = 0
            try {
                uris.forEach { deleted += contentResolver.delete(it, null, null) }
                if (deleted == uris.size) {
                    toast(if (requestCode == REQ_DELETE_ALL) "全データを削除しました" else "削除しました")
                    refresh()
                } else toast("削除できませんでした")
            } catch (e: RecoverableSecurityException) {
                startIntentSenderForResult(e.userAction.actionIntent.intentSender, requestCode, null, 0, 0, 0)
            }
        } catch (_: Throwable) {
            toast("削除できませんでした")
        }
    }

    @Deprecated("Deprecated in Android")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK) return
        when (requestCode) {
            REQ_DELETE_ONE -> {
                toast("削除しました")
                refresh()
            }
            REQ_DELETE_ALL -> {
                toast("全データを削除しました")
                refresh()
            }
            REQ_WRITE -> {
                val oldName = pendingRenameOld
                val newName = pendingRenameNew
                pendingRenameOld = null
                pendingRenameNew = null
                if (oldName != null && newName != null) {
                    if (!renameFolder(oldName, newName)) toast("名前を変更できませんでした")
                }
            }
        }
    }

    private fun queryUrisForRelativePath(path: String): List<Uri> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return emptyList()
        val uris = mutableListOf<Uri>()
        contentResolver.query(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            arrayOf(MediaStore.Downloads._ID),
            "${MediaStore.Downloads.RELATIVE_PATH} = ?",
            arrayOf(path),
            null
        )?.use { c ->
            val idIndex = c.getColumnIndexOrThrow(MediaStore.Downloads._ID)
            while (c.moveToNext()) {
                uris += ContentUris.withAppendedId(MediaStore.Downloads.EXTERNAL_CONTENT_URI, c.getLong(idIndex))
            }
        }
        return uris
    }

    private fun queryAllRecordUris(): List<Uri> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return emptyList()
        val prefix = "${Environment.DIRECTORY_DOWNLOADS}/GreenReaderRecords/"
        val uris = mutableListOf<Uri>()
        contentResolver.query(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            arrayOf(MediaStore.Downloads._ID),
            "${MediaStore.Downloads.RELATIVE_PATH} LIKE ?",
            arrayOf("$prefix%"),
            null
        )?.use { c ->
            val idIndex = c.getColumnIndexOrThrow(MediaStore.Downloads._ID)
            while (c.moveToNext()) {
                uris += ContentUris.withAppendedId(MediaStore.Downloads.EXTERNAL_CONTENT_URI, c.getLong(idIndex))
            }
        }
        return uris
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
