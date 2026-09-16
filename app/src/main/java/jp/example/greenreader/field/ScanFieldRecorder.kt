package jp.example.greenreader.field

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import jp.example.greenreader.analysis.GrainReport
import jp.example.greenreader.analysis.PuttAdvisor
import jp.example.greenreader.analysis.SlopeReport
import jp.example.greenreader.analysis.Vec3
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Saves one complete scan package for later algorithm debugging/calibration.
 *
 * Android 10+:
 *   Download/GreenReaderRecords/scan_<timestamp>/
 *     camera.jpg
 *     metadata.json
 *     depth_points.csv
 *     slope_segments.csv
 *
 * Older Android versions use the app external-files directory.
 */
object ScanFieldRecorder {
    private const val ROOT = "GreenReaderRecords"

    data class CaptureMeta(
        val appVersion: String,
        val trackingState: String,
        val viewportWidth: Int,
        val viewportHeight: Int,
        val cameraTranslation: FloatArray,
        val cameraQuaternion: FloatArray,
        val ballScreenX: Float?,
        val ballScreenY: Float?,
        val cupScreenX: Float?,
        val cupScreenY: Float?
    )

    fun save(
        context: Context,
        bitmap: Bitmap,
        points: List<Vec3>,
        ball: Vec3,
        cup: Vec3,
        report: SlopeReport,
        advice: PuttAdvisor.Advice,
        grain: GrainReport?,
        meta: CaptureMeta
    ): String {
        val id = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val folder = "scan_$id"
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            saveModern(context, folder, bitmap, points, ball, cup, report, advice, grain, meta)
            "Download/$ROOT/$folder"
        } else {
            saveLegacy(context, folder, bitmap, points, ball, cup, report, advice, grain, meta)
        }
    }

    private fun saveModern(
        context: Context,
        folder: String,
        bitmap: Bitmap,
        points: List<Vec3>,
        ball: Vec3,
        cup: Vec3,
        report: SlopeReport,
        advice: PuttAdvisor.Advice,
        grain: GrainReport?,
        meta: CaptureMeta
    ) {
        val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
        writeDownload(context, rel, "camera.jpg", "image/jpeg") { out ->
            if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) error("camera.jpg write failed")
        }
        writeDownload(context, rel, "metadata.json", "application/json") { out ->
            out.bufferedWriter().use { it.write(metadataJson(ball, cup, report, advice, grain, meta, points.size)) }
        }
        writeDownload(context, rel, "depth_points.csv", "text/csv") { out ->
            out.bufferedWriter().use { w ->
                w.write("index,x_m,y_m,z_m\n")
                points.forEachIndexed { i, p ->
                    w.write("$i,${f(p.x)},${f(p.y)},${f(p.z)}\n")
                }
            }
        }
        writeDownload(context, rel, "slope_segments.csv", "text/csv") { out ->
            out.bufferedWriter().use { w ->
                w.write("index,start_m,end_m,longitudinal_percent,cross_percent,elevation_m,sample_count\n")
                report.segments.forEachIndexed { i, s ->
                    w.write("$i,${f(s.startMeters)},${f(s.endMeters)},${f(s.longitudinalPercent)},${f(s.crossPercent)},${f(s.elevationMeters)},${s.sampleCount}\n")
                }
            }
        }
    }

    private fun writeDownload(
        context: Context,
        relativePath: String,
        name: String,
        mime: String,
        writer: (java.io.OutputStream) -> Unit
    ) {
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, name)
            put(MediaStore.Downloads.MIME_TYPE, mime)
            put(MediaStore.Downloads.RELATIVE_PATH, relativePath)
        }
        val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: error("Cannot create $name")
        context.contentResolver.openOutputStream(uri, "w")?.use(writer)
            ?: error("Cannot write $name")
    }

    private fun saveLegacy(
        context: Context,
        folder: String,
        bitmap: Bitmap,
        points: List<Vec3>,
        ball: Vec3,
        cup: Vec3,
        report: SlopeReport,
        advice: PuttAdvisor.Advice,
        grain: GrainReport?,
        meta: CaptureMeta
    ): String {
        val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
        File(dir, "camera.jpg").outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, 92, it) }
        File(dir, "metadata.json").writeText(metadataJson(ball, cup, report, advice, grain, meta, points.size))
        File(dir, "depth_points.csv").bufferedWriter().use { w ->
            w.write("index,x_m,y_m,z_m\n")
            points.forEachIndexed { i, p -> w.write("$i,${f(p.x)},${f(p.y)},${f(p.z)}\n") }
        }
        File(dir, "slope_segments.csv").bufferedWriter().use { w ->
            w.write("index,start_m,end_m,longitudinal_percent,cross_percent,elevation_m,sample_count\n")
            report.segments.forEachIndexed { i, s ->
                w.write("$i,${f(s.startMeters)},${f(s.endMeters)},${f(s.longitudinalPercent)},${f(s.crossPercent)},${f(s.elevationMeters)},${s.sampleCount}\n")
            }
        }
        return dir.absolutePath
    }

    private fun metadataJson(
        ball: Vec3,
        cup: Vec3,
        report: SlopeReport,
        advice: PuttAdvisor.Advice,
        grain: GrainReport?,
        meta: CaptureMeta,
        rawPointCount: Int
    ): String {
        fun vec(v: Vec3) = "{\"x\":${f(v.x)},\"y\":${f(v.y)},\"z\":${f(v.z)}}"
        fun arr(a: FloatArray) = a.joinToString(prefix = "[", postfix = "]") { f(it) }
        fun nullable(v: Float?) = v?.let(::f) ?: "null"
        val grainJson = if (grain == null) "null" else
            "{\"axis_degrees\":${f(grain.axisDegrees)},\"confidence\":${f(grain.confidence)},\"note\":\"${escape(grain.note)}\"}"
        return """{
  \"schema_version\": 1,
  \"app_version\": \"${escape(meta.appVersion)}\",
  \"tracking_state\": \"${escape(meta.trackingState)}\",
  \"viewport\": {\"width\": ${meta.viewportWidth}, \"height\": ${meta.viewportHeight}},
  \"camera_translation\": ${arr(meta.cameraTranslation)},
  \"camera_quaternion\": ${arr(meta.cameraQuaternion)},
  \"ball_world\": ${vec(ball)},
  \"cup_world\": ${vec(cup)},
  \"ball_screen\": {\"x\": ${nullable(meta.ballScreenX)}, \"y\": ${nullable(meta.ballScreenY)}},
  \"cup_screen\": {\"x\": ${nullable(meta.cupScreenX)}, \"y\": ${nullable(meta.cupScreenY)}},
  \"raw_depth_point_count\": $rawPointCount,
  \"analysis_point_count\": ${report.pointCount},
  \"distance_m\": ${f(report.distanceMeters)},
  \"overall_longitudinal_percent\": ${f(report.overallLongitudinalPercent)},
  \"overall_cross_percent\": ${f(report.overallCrossPercent)},
  \"aim_offset_cm\": ${f(advice.aimOffsetCm)},
  \"effective_distance_m\": ${f(advice.effectiveDistanceM)},
  \"advice_warning\": \"${escape(advice.warning)}\",
  \"grain\": $grainJson
}
"""
    }

    private fun f(v: Float) = String.format(Locale.US, "%.6f", v)
    private fun escape(s: String) = s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
}
