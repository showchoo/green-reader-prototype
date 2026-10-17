package jp.example.greenreader.precision

import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject

/**
 * Read-only discovery of public Android Camera2 DEPTH16 capabilities.
 *
 * Does not open a camera, perform scanning or assert ToF identity. Hardware
 * presence and access from apps are different questions. Running while ARCore
 * owns the camera is safe because we read characteristics only.
 */
object PrecisionCamera2DepthProbe {
    data class Result(
        val state: String,
        val visibleCameraCount: Int,
        val probedCameraCount: Int,
        val depth16CameraCount: Int,
        val errorCount: Int,
        val json: String
    )

    fun classify(visible: Int, probed: Int, depth16: Int, errors: Int): String {
        if (depth16 > 0) return "PUBLIC_CAMERA2_DEPTH16"
        if (visible <= 0 || probed <= 0 || errors > 0)
            return "INDETERMINATE"
        return "NO_PUBLIC_CAMERA2_DEPTH16"
    }

    private fun dimensions(
        c: CameraCharacteristics, format: Int
    ): JSONArray {
        val array=JSONArray()
        val sizes=try {
            c.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                ?.getOutputSizes(format)
        } catch (_:Throwable) { null }
        sizes?.forEach { size ->
            array.put(size.width.toString() + "x" + size.height)
        }
        return array
    }

    fun probe(context: Context): Result {
        val cameras=JSONArray()
        val errors=JSONArray()
        val manager=context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val visibleIds=try { manager.cameraIdList.toList() }
        catch (e:Exception) {
            errors.put("cameraIdList:" + e.javaClass.simpleName)
            emptyList()
        }
        val allIds=LinkedHashSet<String>()
        allIds.addAll(visibleIds)
        // Camera2 may advertise physical cameras only through a logical
        // camera. These identifiers can be queried on Android 10+.
        for (id in visibleIds) {
            try {
                val c=manager.getCameraCharacteristics(id)
                allIds.addAll(c.physicalCameraIds)
            } catch (e:Exception) {
                errors.put("logicalCharacteristics:" + id +
                    ":" + e.javaClass.simpleName)
            }
        }

        var successfullyProbed=0
        var depth16Count=0
        for (id in allIds) {
            try {
                val c=manager.getCameraCharacteristics(id)
                val caps=c.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)
                    ?: intArrayOf()
                val advertised=caps.contains(
                    CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT)
                val dep16=dimensions(c,ImageFormat.DEPTH16)
                val pointCloud=dimensions(c,ImageFormat.DEPTH_POINT_CLOUD)
                val depth16Available=advertised && dep16.length()>0
                if(depth16Available)depth16Count++
                successfullyProbed++
                val obj=JSONObject()
                    .put("id",id)
                    .put("visible_id",visibleIds.contains(id))
                    .put("lens_facing",c.get(CameraCharacteristics.LENS_FACING))
                    .put("hardware_level",
                        c.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL))
                    .put("depth_output_advertised",advertised)
                    .put("depth16_output_sizes",dep16)
                    .put("point_cloud_output_sizes",pointCloud)
                    .put("depth16_publicly_accessible_candidate",depth16Available)
                    .put("depth_is_exclusive",
                        c.get(CameraCharacteristics.DEPTH_DEPTH_IS_EXCLUSIVE))
                    .put("intrinsics_present",
                        c.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION)!=null)
                    .put("lens_pose_present",
                        c.get(CameraCharacteristics.LENS_POSE_ROTATION)!=null &&
                            c.get(CameraCharacteristics.LENS_POSE_TRANSLATION)!=null)
                cameras.put(obj)
            } catch (e:Exception) {
                errors.put("camera:" + id + ":" + e.javaClass.simpleName)
            }
        }

        val state=classify(
            visibleIds.size,successfullyProbed,depth16Count,errors.length())
        val json=JSONObject()
            .put("schema_version",1)
            .put("kind","CAMERA2_READ_ONLY_HARDWARE_RESEARCH")
            .put("manufacturer",Build.MANUFACTURER)
            .put("model",Build.MODEL)
            .put("sdk",Build.VERSION.SDK_INT)
            .put("result",state)
            .put("visible_camera_count",visibleIds.size)
            .put("probed_camera_count",successfullyProbed)
            .put("depth16_candidate_camera_count",depth16Count)
            .put("errors",errors)
            .put("cameras",cameras)
            .put("public_depth16_is_verified_measurement",false)
            .put("tof_physical_sensor_identity_verified",false)
            .put("accuracy_certified",false)
            .put("notes",
                "Read only Camera2 reported capabilities. Does not open sensors, " +
                "prove ToF hardware identity, or certify slope accuracy.")
            .toString(2)
        return Result(state,visibleIds.size,successfullyProbed,depth16Count,
            errors.length(),json)
    }
}
