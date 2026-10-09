package jp.example.greenreader.field

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Archives app-owned MediaStore records; never scans unrelated Downloads.
 * Session/Putt/Scan layout is maintained inside each ZIP for offline analysis.
 */
object DriveBackupArchive {
    data class Item(val uri: Uri, val relativeName: String, val bytes: Long, val modified: Long)
    data class Session(val name: String, val items: List<Item>) {
        fun fingerprint(): String {
            val digest = MessageDigest.getInstance("SHA-256")
            for (item in items.sortedBy { it.relativeName }) {
                val sig = item.relativeName + "\u0000" +
                    item.bytes.toString() + "\u0000" + item.modified.toString() + "\n"
                digest.update(sig.toByteArray(Charsets.UTF_8))
            }
            return digest.digest().joinToString("") {
                String.format(Locale.US, "%02x", it.toInt() and 0xff)
            }
        }
        val zipName: String get() = name + ".zip"
    }

    fun sessions(context: Context): List<Session> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return emptyList()
        val base = MediaStore.Downloads.EXTERNAL_CONTENT_URI
        val projection = arrayOf(
            MediaStore.Downloads._ID,
            MediaStore.Downloads.DISPLAY_NAME,
            MediaStore.Downloads.RELATIVE_PATH,
            MediaStore.Downloads.SIZE,
            MediaStore.Downloads.DATE_MODIFIED
        )
        val all = HashMap<String, MutableList<Item>>()
        // Android 10+ MediaStore permits reading files inserted by this app
        // without broad storage permissions.
        context.contentResolver.query(base, projection, null, null, null)?.use { cursor ->
            val idIndex = cursor.getColumnIndexOrThrow(MediaStore.Downloads._ID)
            val nameIndex = cursor.getColumnIndexOrThrow(MediaStore.Downloads.DISPLAY_NAME)
            val pathIndex = cursor.getColumnIndexOrThrow(MediaStore.Downloads.RELATIVE_PATH)
            val sizeIndex = cursor.getColumnIndexOrThrow(MediaStore.Downloads.SIZE)
            val dateIndex = cursor.getColumnIndexOrThrow(MediaStore.Downloads.DATE_MODIFIED)
            while (cursor.moveToNext()) {
                val rawPath = cursor.getString(pathIndex) ?: continue
                val start = "Download/GreenReaderRecords/"
                if (!rawPath.startsWith(start)) continue
                val parts = rawPath.removePrefix(start).trim('/').split('/')
                if (parts.size != 3 ||
                    !parts[0].startsWith("Session_") ||
                    !parts[1].startsWith("Putt_") ||
                    !parts[2].startsWith("Scan_")
                ) continue
                val filename = cursor.getString(nameIndex) ?: continue
                if (filename.isBlank() || filename.contains('/') ||
                    filename.contains('\\') || filename == "..") continue
                val session = parts[0]
                if (!session.matches(Regex("Session_[A-Za-z0-9_-]{1,100}"))) continue
                val relative = parts[1] + "/" + parts[2] + "/" + filename
                all.getOrPut(session) { ArrayList() }.add(Item(
                    uri = ContentUris.withAppendedId(base, cursor.getLong(idIndex)),
                    relativeName = relative,
                    bytes = cursor.getLong(sizeIndex).coerceAtLeast(0),
                    modified = cursor.getLong(dateIndex)
                ))
            }
        }
        return all.mapNotNull { (name, items) ->
            // record_identity is written near the end of each completed scan.
            val completeScanDirs = items
                .filter { it.relativeName.endsWith("/record_identity.json") }
                .map { it.relativeName.substringBeforeLast('/') }.toSet()
            val completeItems = items.filter {
                it.relativeName.substringBeforeLast('/') in completeScanDirs
            }.sortedBy { it.relativeName }
            if (completeItems.isEmpty()) null else Session(name, completeItems)
        }.sortedBy { it.name }
    }

    fun zip(context: Context, session: Session): File {
        val tmp = File.createTempFile("greenreader_session_", ".zip", context.cacheDir)
        try {
            ZipOutputStream(FileOutputStream(tmp).buffered()).use { out ->
                for (item in session.items) {
                    val entry = item.relativeName
                    if (entry.startsWith("/") || entry.split('/').any { it == ".." || it == "." })
                        error("Invalid archive entry")
                    out.putNextEntry(ZipEntry(entry))
                    val input = context.contentResolver.openInputStream(item.uri)
                        ?: error("Saved scan no longer readable: " + entry)
                    input.use { it.copyTo(out, 64 * 1024) }
                    out.closeEntry()
                }
            }
            return tmp
        } catch (e: Exception) {
            tmp.delete()
            throw e
        }
    }
}
