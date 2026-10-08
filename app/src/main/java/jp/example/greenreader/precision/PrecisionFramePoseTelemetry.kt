package jp.example.greenreader.precision

import java.util.Locale

/**
 * Low-cost camera-pose telemetry for offline Depth bias analysis.
 * Depth image time and current ARCore frame time are saved separately:
 * a pose sampled on the current Frame is NOT necessarily a pose measured
 * at the exact depth-image timestamp.
 *
 * This class is diagnostic-only. It never changes a slope, a scan verdict,
 * or the number of accepted Depth cells.
 */
object PrecisionFramePoseTelemetry {
    data class Entry(
        val depthTimestampNs: Long,
        val cameraFrameTimestampNs: Long,
        val source: String,
        val x: Float,
        val y: Float,
        val z: Float,
        val qx: Float,
        val qy: Float,
        val qz: Float,
        val qw: Float,
        // Unit ray axes expressed in the same gravity-aligned, ball-relative
        // frame as precision_depth_points.csv. These enable frame-relative
        // off-axis geometry without assuming an ARCore world frame is fixed.
        val forwardLocalX: Float = 0f,
        val forwardLocalY: Float = 0f,
        val forwardLocalZ: Float = -1f,
        val rightLocalX: Float = 1f,
        val rightLocalY: Float = 0f,
        val rightLocalZ: Float = 0f,
        // Intrinsics are expressed in the pixel coordinates named by basis.
        // raw_texture_scaled = native Raw Depth pixel coordinates;
        // cpu_image_pixels = transformed CPU image pixel coordinates for Full.
        val projectionBasis: String = "unknown",
        val projectionWidth: Int = 0,
        val projectionHeight: Int = 0,
        val focalX: Float = 0f,
        val focalY: Float = 0f,
        val principalX: Float = 0f,
        val principalY: Float = 0f
    )

    class Buffer(private val maxRecords: Int = 256) {
        init { require(maxRecords >= 1) }
        private val records = LinkedHashMap<Pair<Long, String>, Entry>()
        private var dropped = 0

        fun clear() {
            records.clear()
            dropped = 0
        }

        fun size(): Int = records.size
        fun droppedCount(): Int = dropped

        fun record(value: Entry) {
            if (value.source != "raw" && value.source != "full") return
            if (!listOf(value.x, value.y, value.z, value.qx, value.qy,
                        value.qz, value.qw,
                        value.forwardLocalX, value.forwardLocalY, value.forwardLocalZ,
                        value.rightLocalX, value.rightLocalY, value.rightLocalZ,
                        value.focalX, value.focalY, value.principalX, value.principalY)
                    .all { it.isFinite() }) return
            if (value.projectionBasis != "unknown" &&
                (value.projectionBasis !in setOf("raw_texture_scaled", "cpu_image_pixels") ||
                 value.projectionWidth <= 0 || value.projectionHeight <= 0 ||
                 value.focalX <= 0f || value.focalY <= 0f)) return
            val key = value.depthTimestampNs to value.source
            if (records.containsKey(key)) return
            if (records.size >= maxRecords) {
                val first = records.keys.first()
                records.remove(first)
                dropped++
            }
            records[key] = value
        }

        /** Embed a machine-readable CSV section into collector_diagnostics.txt. */
        fun toDiagnosticText(): String = buildString {
            append("FRAME_POSE_V1_BEGIN records=").append(records.size)
                .append(" dropped=").append(dropped).append('\n')
            append("depth_timestamp_ns,camera_frame_timestamp_ns,source,")
            append("camera_local_x_m,camera_local_y_m,camera_local_z_m,")
            append("camera_world_qx,camera_world_qy,camera_world_qz,camera_world_qw,")
            append("camera_forward_local_x,camera_forward_local_y,camera_forward_local_z,")
            append("camera_right_local_x,camera_right_local_y,camera_right_local_z,")
            append("projection_basis,projection_width,projection_height,")
            append("intrinsics_fx,intrinsics_fy,intrinsics_cx,intrinsics_cy")
                .append('\n')
            fun format(v: Float) = String.format(Locale.US, "%.6f", v)
            for (v in records.values) {
                append(v.depthTimestampNs).append(',')
                append(v.cameraFrameTimestampNs).append(',')
                append(v.source).append(',')
                append(format(v.x)).append(',')
                append(format(v.y)).append(',')
                append(format(v.z)).append(',')
                append(format(v.qx)).append(',')
                append(format(v.qy)).append(',')
                append(format(v.qz)).append(',')
                append(format(v.qw)).append(',')
                append(format(v.forwardLocalX)).append(',')
                append(format(v.forwardLocalY)).append(',')
                append(format(v.forwardLocalZ)).append(',')
                append(format(v.rightLocalX)).append(',')
                append(format(v.rightLocalY)).append(',')
                append(format(v.rightLocalZ)).append(',')
                append(v.projectionBasis).append(',')
                append(v.projectionWidth).append(',')
                append(v.projectionHeight).append(',')
                append(format(v.focalX)).append(',')
                append(format(v.focalY)).append(',')
                append(format(v.principalX)).append(',')
                append(format(v.principalY)).append('\n')
            }
            append("FRAME_POSE_V1_END")
        }
    }
}
