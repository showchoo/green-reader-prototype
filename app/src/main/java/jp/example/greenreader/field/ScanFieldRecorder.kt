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
import jp.example.greenreader.precision.PrecisionDepthPoint
import jp.example.greenreader.precision.PrecisionScanQuality
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

    data class RecordIdentity(
        val sessionId: String,
        val puttId: Int,
        val scanIndex: Int,
        val scanStartedAtEpochMs: Long,
        val scanFinishedAtEpochMs: Long
    )

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
        val cupScreenY: Float?,
        val arCoreDepthSupported: Boolean = false
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
        meta: CaptureMeta,
        precisionPoints: List<PrecisionDepthPoint> = emptyList(),
        precisionDiagnostic: String = "",
        markerDiagnostic: String = "",
        collectorDiagnostic: String = ""
    ): String {
        val id = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val folder = "scan_$id"
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            saveModern(context, folder, bitmap, points, ball, cup, report, advice, grain, meta)
            savePrecisionExtrasModern(context, folder, precisionPoints, precisionDiagnostic, markerDiagnostic, collectorDiagnostic)
            "Download/$ROOT/$folder"
        } else {
            val path = saveLegacy(context, folder, bitmap, points, ball, cup, report, advice, grain, meta)
            savePrecisionExtrasLegacy(File(path), precisionPoints, precisionDiagnostic, markerDiagnostic, collectorDiagnostic)
            path
        }
    }


    fun saveGrouped(
        context: Context,
        bitmap: Bitmap,
        points: List<Vec3>,
        ball: Vec3,
        cup: Vec3,
        report: SlopeReport,
        advice: PuttAdvisor.Advice,
        grain: GrainReport?,
        meta: CaptureMeta,
        precisionPoints: List<PrecisionDepthPoint>,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String,
        identity: RecordIdentity,
        quality: PrecisionScanQuality?
    ): String {
        val folder = groupedFolder(identity, failed = false)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            saveModern(context, folder, bitmap, points, ball, cup, report, advice, grain, meta)
            savePrecisionExtrasModern(
                context, folder, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            saveRecordExtrasModern(context, folder, identity, meta, quality)
            "Download/$ROOT/$folder"
        } else {
            val path = saveLegacy(context, folder, bitmap, points, ball, cup, report, advice, grain, meta)
            val dir = File(path)
            savePrecisionExtrasLegacy(
                dir, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            saveRecordExtrasLegacy(dir, identity, meta, quality)
            path
        }
    }

    fun saveFailureGrouped(
        context: Context,
        precisionPoints: List<PrecisionDepthPoint>,
        ball: Vec3?,
        cup: Vec3?,
        reason: String,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String,
        meta: CaptureMeta,
        identity: RecordIdentity,
        quality: PrecisionScanQuality?
    ): String {
        val folder = groupedFolder(identity, failed = true)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            writeDownload(context, rel, "metadata.json", "application/json") { out ->
                out.bufferedWriter().use {
                    it.write(failureMetadataJson(ball, cup, reason, meta, precisionPoints.size))
                }
            }
            savePrecisionExtrasModern(
                context, folder, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            saveRecordExtrasModern(context, folder, identity, meta, quality)
            "Download/$ROOT/$folder"
        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            File(dir, "metadata.json").writeText(
                failureMetadataJson(ball, cup, reason, meta, precisionPoints.size)
            )
            savePrecisionExtrasLegacy(
                dir, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            saveRecordExtrasLegacy(dir, identity, meta, quality)
            dir.absolutePath
        }
    }

    private fun groupedFolder(identity: RecordIdentity, failed: Boolean): String {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val session = identity.sessionId.replace(Regex("[^A-Za-z0-9_-]"), "_")
        val putt = String.format(Locale.US, "Putt_%03d", identity.puttId)
        val scan = String.format(Locale.US, "Scan_%02d", identity.scanIndex)
        return "Session_$session/$putt/${scan}_$stamp" + if (failed) "_FAILED" else ""
    }

    private fun saveRecordExtrasModern(
        context: Context,
        folder: String,
        identity: RecordIdentity,
        meta: CaptureMeta,
        quality: PrecisionScanQuality?
    ) {
        val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
        writeDownload(context, rel, "record_identity.json", "application/json") { out ->
            out.bufferedWriter().use { it.write(recordIdentityJson(context, identity, meta)) }
        }
        quality?.let { q ->
            writeDownload(context, rel, "scan_quality.json", "application/json") { out ->
                out.bufferedWriter().use { it.write(qualityJson(q)) }
            }
        }
    }

    private fun saveRecordExtrasLegacy(
        dir: File,
        identity: RecordIdentity,
        meta: CaptureMeta,
        quality: PrecisionScanQuality?
    ) {
        File(dir, "record_identity.json").writeText(recordIdentityJson(null, identity, meta))
        quality?.let { File(dir, "scan_quality.json").writeText(qualityJson(it)) }
    }

    private fun recordIdentityJson(
        context: Context?,
        identity: RecordIdentity,
        meta: CaptureMeta
    ): String {
        return """{
  "schema_version": 3,
  "session_id": "${escape(identity.sessionId)}",
  "putt_id": ${identity.puttId},
  "scan_index": ${identity.scanIndex},
  "scan_started_at_epoch_ms": ${identity.scanStartedAtEpochMs},
  "scan_finished_at_epoch_ms": ${identity.scanFinishedAtEpochMs},
  "app_version": "${escape(meta.appVersion)}",
  "manufacturer": "${escape(Build.MANUFACTURER)}",
  "model": "${escape(Build.MODEL)}",
  "device": "${escape(Build.DEVICE)}",
  "sdk_int": ${Build.VERSION.SDK_INT},
  "arcore_depth_supported": ${meta.arCoreDepthSupported}
}
"""
    }

    private fun qualityJson(q: PrecisionScanQuality): String {
        fun jf(v: Float): String = if (v.isFinite()) f(v) else "null"
        val guidance = q.guidance.joinToString(prefix = "[", postfix = "]") {
            "\"${escape(it)}\""
        }
        return """{
  "score": ${q.score},
  "tier": "${escape(q.tier)}",
  "estimated_slope_uncertainty_percent": ${jf(q.estimatedSlopeUncertaintyPercent)},
  "valid_window_count": ${q.validWindowCount},
  "window_long_sd_percent": ${jf(q.windowLongStdDevPercent)},
  "window_cross_sd_percent": ${jf(q.windowCrossStdDevPercent)},
  "median_cell_mad_mm": ${jf(q.medianCellMadMm)},
  "median_local_rmse_mm": ${jf(q.medianLocalRmseMm)},
  "corridor_coverage": ${jf(q.corridorCoverage)},
  "source_point_count": ${q.sourcePointCount},
  "unique_depth_frames": ${q.uniqueDepthFrames},
  "ground_cell_count": ${q.groundCellCount},
  "candidate_cell_count": ${q.candidateCellCount},
  "raw_accepted_frames": ${q.rawAcceptedFrames},
  "full_accepted_frames": ${q.fullAcceptedFrames},
  "duplicate_depth_frames": ${q.duplicateDepthFrames},
  "tracking_ratio": ${jf(q.trackingRatio)},
  "pose_jump_count": ${q.poseJumpCount},
  "camera_travel_m": ${jf(q.cameraTravelMeters)},
  "guidance": $guidance
}"""
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

    fun saveFailure(
        context: Context,
        precisionPoints: List<PrecisionDepthPoint>,
        ball: Vec3?,
        cup: Vec3?,
        reason: String,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String,
        meta: CaptureMeta
    ): String {
        val id = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val folder = "scan_${id}_FAILED"
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            writeDownload(context, rel, "metadata.json", "application/json") { out ->
                out.bufferedWriter().use {
                    it.write(failureMetadataJson(ball, cup, reason, meta, precisionPoints.size))
                }
            }
            savePrecisionExtrasModern(
                context, folder, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            "Download/$ROOT/$folder"
        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            File(dir, "metadata.json").writeText(
                failureMetadataJson(ball, cup, reason, meta, precisionPoints.size)
            )
            savePrecisionExtrasLegacy(
                dir, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            dir.absolutePath
        }
    }

    private fun savePrecisionExtrasModern(
        context: Context,
        folder: String,
        precisionPoints: List<PrecisionDepthPoint>,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String
    ) {
        val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
        writeDownload(context, rel, "precision_depth_points.csv", "text/csv") { out ->
            writePrecisionPoints(out, precisionPoints)
        }
        writeDownload(context, rel, "precision_diagnostics.txt", "text/plain") { out ->
            out.bufferedWriter().use { it.write(precisionDiagnostic) }
        }
        writeDownload(context, rel, "marker_diagnostics.txt", "text/plain") { out ->
            out.bufferedWriter().use { it.write(markerDiagnostic) }
        }
        writeDownload(context, rel, "collector_diagnostics.txt", "text/plain") { out ->
            out.bufferedWriter().use { it.write(collectorDiagnostic) }
        }
    }

    private fun savePrecisionExtrasLegacy(
        dir: File,
        precisionPoints: List<PrecisionDepthPoint>,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String
    ) {
        File(dir, "precision_depth_points.csv").outputStream().use { out ->
            writePrecisionPoints(out, precisionPoints)
        }
        File(dir, "precision_diagnostics.txt").writeText(precisionDiagnostic)
        File(dir, "marker_diagnostics.txt").writeText(markerDiagnostic)
        File(dir, "collector_diagnostics.txt").writeText(collectorDiagnostic)
    }

    private fun writePrecisionPoints(
        out: java.io.OutputStream,
        points: List<PrecisionDepthPoint>
    ) {
        out.bufferedWriter().use { w ->
            w.write("index,x_m,y_m,z_m,confidence,frame_timestamp_ns\n")
            points.forEachIndexed { i, p ->
                w.write(
                    "$i,${f(p.x)},${f(p.y)},${f(p.z)},${f(p.confidence)},${p.frameTimestampNs}\n"
                )
            }
        }
    }

    private fun failureMetadataJson(
        ball: Vec3?,
        cup: Vec3?,
        reason: String,
        meta: CaptureMeta,
        precisionPointCount: Int
    ): String {
        fun vecOrNull(v: Vec3?) = if (v == null) "null" else
            "{\"x\":${f(v.x)},\"y\":${f(v.y)},\"z\":${f(v.z)}}"
        fun arr(a: FloatArray) = a.joinToString(prefix = "[", postfix = "]") { f(it) }
        return """{
  \"schema_version\": 2,
  \"outcome\": \"failure\",
  \"reason\": \"${escape(reason)}\",
  \"app_version\": \"${escape(meta.appVersion)}\",
  \"tracking_state\": \"${escape(meta.trackingState)}\",
  \"viewport\": {\"width\": ${meta.viewportWidth}, \"height\": ${meta.viewportHeight}},
  \"camera_translation\": ${arr(meta.cameraTranslation)},
  \"camera_quaternion\": ${arr(meta.cameraQuaternion)},
  \"ball_world\": ${vecOrNull(ball)},
  \"cup_world\": ${vecOrNull(cup)},
  \"precision_point_count\": $precisionPointCount
}
"""
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
