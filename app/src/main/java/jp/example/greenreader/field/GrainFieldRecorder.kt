package jp.example.greenreader.field

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import jp.example.greenreader.analysis.GrainReport
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class GrainSavedRecord(
    val id: String,
    val imageLocation: String,
    val csvLocation: String,
    val csvUri: Uri?,
    val report: GrainReport,
    val pose: FloatArray,
    val quaternion: FloatArray,
    var label: String = "unlabeled"
)

object GrainFieldRecorder {
    private const val FOLDER = "GreenReaderRecords"

    fun save(
        context: Context,
        bitmap: Bitmap,
        report: GrainReport,
        pose: FloatArray,
        quaternion: FloatArray
    ): GrainSavedRecord {
        val id = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val imageName = "grain_$id.jpg"
        val csvName = "grain_$id.csv"

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val resolver = context.contentResolver
            val imageValues = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, imageName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/$FOLDER")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val imageUri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, imageValues)
                ?: error("画像の保存先を作成できません")
            resolver.openOutputStream(imageUri)?.use { out ->
                if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) error("画像保存に失敗しました")
            } ?: error("画像を書き込めません")
            imageValues.clear()
            imageValues.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(imageUri, imageValues, null, null)

            val csvValues = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, csvName)
                put(MediaStore.Downloads.MIME_TYPE, "text/csv")
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/$FOLDER")
            }
            val csvUri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, csvValues)
                ?: error("CSVの保存先を作成できません")
            writeCsv(context, csvUri, id, report, pose, quaternion, "unlabeled")

            GrainSavedRecord(
                id = id,
                imageLocation = "Pictures/$FOLDER/$imageName",
                csvLocation = "Download/$FOLDER/$csvName",
                csvUri = csvUri,
                report = report,
                pose = pose,
                quaternion = quaternion
            )
        } else {
            val base = File(context.getExternalFilesDir(null), FOLDER).apply { mkdirs() }
            val imageFile = File(base, imageName)
            imageFile.outputStream().use { out -> bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out) }
            val csvFile = File(base, csvName)
            csvFile.writeText(csvText(id, report, pose, quaternion, "unlabeled"))
            GrainSavedRecord(
                id = id,
                imageLocation = imageFile.absolutePath,
                csvLocation = csvFile.absolutePath,
                csvUri = Uri.fromFile(csvFile),
                report = report,
                pose = pose,
                quaternion = quaternion
            )
        }
    }

    fun relabel(context: Context, record: GrainSavedRecord, label: String): GrainSavedRecord {
        record.label = label
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && record.csvUri != null) {
            writeCsv(context, record.csvUri, record.id, record.report, record.pose, record.quaternion, label)
        } else {
            val uri = record.csvUri
            if (uri?.scheme == "file") {
                File(requireNotNull(uri.path)).writeText(csvText(record.id, record.report, record.pose, record.quaternion, label))
            }
        }
        return record
    }

    private fun writeCsv(
        context: Context,
        uri: Uri,
        id: String,
        report: GrainReport,
        pose: FloatArray,
        quaternion: FloatArray,
        label: String
    ) {
        context.contentResolver.openOutputStream(uri, "wt")?.bufferedWriter()?.use {
            it.write(csvText(id, report, pose, quaternion, label))
        } ?: error("CSVを書き込めません")
    }

    private fun csvText(
        id: String,
        report: GrainReport,
        pose: FloatArray,
        quaternion: FloatArray,
        label: String
    ): String {
        fun f(v: Float) = String.format(Locale.US, "%.6f", v)
        val header = "id,axis_degrees,confidence,label,tx,ty,tz,qx,qy,qz,qw,note\n"
        val note = report.note.replace("\"", "\"\"")
        val row = listOf(
            id,
            String.format(Locale.US, "%.2f", report.axisDegrees),
            String.format(Locale.US, "%.4f", report.confidence),
            label,
            f(pose.getOrElse(0) { 0f }), f(pose.getOrElse(1) { 0f }), f(pose.getOrElse(2) { 0f }),
            f(quaternion.getOrElse(0) { 0f }), f(quaternion.getOrElse(1) { 0f }),
            f(quaternion.getOrElse(2) { 0f }), f(quaternion.getOrElse(3) { 1f }),
            "\"$note\""
        ).joinToString(",")
        return header + row + "\n"
    }
}
