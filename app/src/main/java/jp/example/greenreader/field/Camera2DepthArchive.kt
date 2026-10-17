package jp.example.greenreader.field

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Independent experimental DEPTH16 session.
 * Only app-owned MediaStore Downloads are written and included in the
 * already user-authorized DriveBackupArchive. No unrelated photos are read.
 *
 * record_identity.json is saved LAST, making it the transaction commit
 * marker for the existing archive worker. No accuracy is asserted.
 */
object Camera2DepthArchive {
    data class Outcome(val savedFolder:String, val frameCount:Int)

    fun save(
        context: Context,
        calibration: String,
        frames: List<File>,
        frameCsv: String,
        gravityCsv: String,
        summaryJson: String
    ): Outcome {
        val stamp=SimpleDateFormat("yyyyMMdd_HHmmss_SSS",Locale.US)
            .format(Date())
        val root="GreenReaderRecords"
        val folder="Session_HW_DEPTH_$stamp/Putt_000/Scan_01_DEPTH16"
        val identity=JSONObject()
            .put("schema_version",1)
            .put("record_kind","camera2_depth16_capture")
            .put("app_version","Precision 11.0 Camera2 Depth研究")
            .put("capture_frame_count",frames.size)
            .put("recorded_at_epoch_ms",System.currentTimeMillis())
            .put("metric_slope_certified",false)
            .put("tof_hardware_identity_verified",false)
            .put("independent_gravity_calibration_verified",false).toString(2)

        if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.Q) {
            val rel=Environment.DIRECTORY_DOWNLOADS + "/$root/$folder"
            fun writeBytes(name:String,mime:String,bytes:ByteArray) {
                val values=ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME,name)
                    put(MediaStore.Downloads.MIME_TYPE,mime)
                    put(MediaStore.Downloads.RELATIVE_PATH,rel)
                }
                val uri=context.contentResolver.insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI,values)
                    ?: error("Could not save "+name)
                context.contentResolver.openOutputStream(uri,"w")?.use {
                    it.write(bytes)
                } ?: error("Could not open "+name)
            }
            writeBytes("camera2_calibration.json","application/json",
                calibration.toByteArray(Charsets.UTF_8))
            for (file in frames.sortedBy { it.name }) {
                require(file.name.matches(Regex("depth_[0-9]{4}\\.bin")))
                writeBytes(file.name,"application/octet-stream",file.readBytes())
            }
            writeBytes("camera2_depth_frames.csv","text/csv",
                frameCsv.toByteArray(Charsets.UTF_8))
            writeBytes("camera2_gravity.csv","text/csv",
                gravityCsv.toByteArray(Charsets.UTF_8))
            writeBytes("camera2_depth_summary.json","application/json",
                summaryJson.toByteArray(Charsets.UTF_8))
            writeBytes("record_identity.json","application/json",
                identity.toByteArray(Charsets.UTF_8))
        } else {
            val out=File(context.getExternalFilesDir(null),"$root/$folder")
                .apply { mkdirs() }
            File(out,"camera2_calibration.json").writeText(calibration)
            for(file in frames)file.copyTo(File(out,file.name),overwrite=true)
            File(out,"camera2_depth_frames.csv").writeText(frameCsv)
            File(out,"camera2_gravity.csv").writeText(gravityCsv)
            File(out,"camera2_depth_summary.json").writeText(summaryJson)
            File(out,"record_identity.json").writeText(identity)
        }
        // Only the existing explicit Drive opt-in controls upload.
        DriveBackupScheduler.onScanSaved(context)
        return Outcome("Download/$root/$folder",frames.size)
    }
}
