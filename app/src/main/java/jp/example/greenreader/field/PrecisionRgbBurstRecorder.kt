package jp.example.greenreader.field

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.media.Image
import android.os.SystemClock
import com.google.ar.core.Frame
import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import jp.example.greenreader.precision.PrecisionYuv420Nv21
import java.io.File
import java.io.FileOutputStream
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.Semaphore
import java.util.concurrent.TimeUnit

/**
 * Opt-in, research-only synchronized CPU-camera RGB sequence.
 *
 * IMPORTANT: not a metric-height estimator, no slope/aim data changed.
 * Capture is bounded (8 fps, 96 images, max 3 YUV images in flight), and
 * stores CPU image plus pose/intrinsics from the SAME ARCore Frame.
 * Every ARCore Image is closed on the renderer thread before processing.
 *
 * Outputs are attached to the same Scan folder BEFORE Drive upload is queued.
 */
object PrecisionRgbBurstRecorder {
    private const val MAX_IMAGES = 96
    private const val PERIOD_NS = 125_000_000L
    private const val JPEG_QUALITY = 83
    private const val MAX_IMU_SAMPLES = 9000
    private const val MAX_PENDING_YUV = 3
    private val io = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "GreenReader-RGB-Research").apply { isDaemon = true }
    }
    private val permits = Semaphore(MAX_PENDING_YUV)
    private val lock = Any()

    private class Capture(val id: String, val dir: File) {
        val rows = ArrayList<String>()
        val imu = ArrayList<String>()
        var closed = false
        var acquired = 0
        var saved = 0
        var unavailable = 0
        var droppedBusy = 0
        var droppedCrop = 0
        var errors = 0
        var lastTimestampNs = 0L
    }

    private var active: Capture? = null
    private val sessions = HashMap<String,Capture>()
    private var sensorManager: SensorManager? = null
    private val listener = object : SensorEventListener {
        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        override fun onSensorChanged(event: SensorEvent) {
            synchronized(lock) {
                val c = active ?: return
                if (c.closed || c.imu.size >= MAX_IMU_SAMPLES) return
                if (event.values.size < 3) return
                c.imu.add(event.timestamp.toString() + "," +
                    SystemClock.elapsedRealtimeNanos() + "," +
                    event.sensor.type + "," +
                    num(event.values[0]) + "," + num(event.values[1]) +
                    "," + num(event.values[2]) + "," + event.accuracy)
            }
        }
    }

    private fun key(identity: ScanFieldRecorder.RecordIdentity): String =
        identity.sessionId + "/" + identity.puttId + "/" + identity.scanIndex

    private fun num(v: Float): String =
        if (v.isFinite()) String.format(Locale.US,"%.7f",v) else ""

    private fun arr(v: FloatArray?, count: Int): String =
        (v ?: FloatArray(count) { Float.NaN }).joinToString(",") { num(it) }

    /**
     * Caller must perform user opt-in before calling this method.
     * One logical SCAN is one independent RGB sequence.
     */
    fun begin(context: Context, identity: ScanFieldRecorder.RecordIdentity) {
        val key=key(identity)
        val dir=File(context.cacheDir,
            "precision_rgb_research/" + key.replace(Regex("[^A-Za-z0-9_/-]"), "_"))
        synchronized(lock) {
            active?.closed = true
            val fresh=Capture(key,dir)
            sessions[key]=fresh
            active=fresh
        }
        dir.mkdirs()
        val manager=context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        sensorManager?.unregisterListener(listener)
        sensorManager=manager
        for (type in intArrayOf(Sensor.TYPE_ACCELEROMETER,
            Sensor.TYPE_GYROSCOPE,Sensor.TYPE_GRAVITY)) {
            manager.getDefaultSensor(type)?.let {
                manager.registerListener(listener,it,SensorManager.SENSOR_DELAY_GAME)
            }
        }
    }

    /** Invoked only on the ARCore GL thread, immediately after Session.update(). */
    fun capture(frame: Frame, ballPose: Pose?, cupPose: Pose?) {
        val c=synchronized(lock) { active }
        if (c==null || c.closed || frame.camera.trackingState!=TrackingState.TRACKING)
            return
        val frameTime=frame.timestamp
        if (frameTime <= 0L) return
        synchronized(lock) {
            if (c.closed || c !== active) return
            if (c.acquired >= MAX_IMAGES ||
                frameTime - c.lastTimestampNs < PERIOD_NS) return
            c.lastTimestampNs=frameTime
        }
        if (!permits.tryAcquire()) {
            synchronized(lock) { c.droppedBusy++ }
            return
        }
        try {
            frame.acquireCameraImage().use { image ->
                if (image.format != ImageFormat.YUV_420_888 ||
                    image.width%2!=0 || image.height%2!=0 ||
                    image.cropRect != Rect(0,0,image.width,image.height)) {
                    synchronized(lock) { c.droppedCrop++ }
                    return@use
                }
                val planes=image.planes
                if (planes.size != 3) {
                    synchronized(lock) { c.droppedCrop++ }
                    return@use
                }
                val nv21=PrecisionYuv420Nv21.pack(image.width,image.height,
                    planes[0].buffer,planes[0].rowStride,planes[0].pixelStride,
                    planes[1].buffer,planes[1].rowStride,planes[1].pixelStride,
                    planes[2].buffer,planes[2].rowStride,planes[2].pixelStride)
                val intr=frame.camera.imageIntrinsics
                val cameraPose=frame.camera.pose
                val sensorPose=try { frame.androidSensorPose } catch (_:Exception) { null }
                val andCameraTime=try { frame.androidCameraTimestamp }
                    catch (_:Exception) { -1L }
                val idx=synchronized(lock) {
                    if (c.closed || c !== active || c.acquired >= MAX_IMAGES)
                        -1 else { c.acquired++; c.acquired }
                }
                if (idx<0) return@use
                val poseTranslation=cameraPose.translation
                val poseQuat=cameraPose.rotationQuaternion
                val row=idx.toString() + "," + frameTime.toString() +
                    "," + image.timestamp + "," + andCameraTime +
                    "," + image.width + "," + image.height + "," +
                    arr(intr.focalLength,2) + "," +
                    arr(intr.principalPoint,2) + "," +
                    arr(intr.imageDimensions.map { it.toFloat() }.toFloatArray(),2) + "," +
                    arr(poseTranslation,3) + "," + arr(poseQuat,4) + "," +
                    arr(sensorPose?.translation,3) + "," +
                    arr(sensorPose?.rotationQuaternion,4) + "," +
                    arr(ballPose?.translation,3) + "," +
                    arr(cupPose?.translation,3) + "," + frame.camera.trackingState.name
                io.execute {
                    try {
                        val dest=File(c.dir,"rgb_" + String.format(Locale.US,"%04d",idx) + ".jpg")
                        FileOutputStream(dest).use { output ->
                            if (!YuvImage(nv21,ImageFormat.NV21,image.width,image.height,null)
                                    .compressToJpeg(Rect(0,0,image.width,image.height),
                                        JPEG_QUALITY,output))
                                throw IllegalStateException("JPEG encoder failed")
                        }
                        synchronized(lock) { c.saved++; c.rows.add(row) }
                    } catch (_:Throwable) {
                        synchronized(lock) { c.errors++ }
                    } finally {
                        permits.release()
                    }
                }
            }
        } catch (e:com.google.ar.core.exceptions.NotYetAvailableException) {
            synchronized(lock) { c.unavailable++ }
            permits.release()
        } catch (_:Throwable) {
            synchronized(lock) { c.errors++ }
            permits.release()
        }
    }

    /**
     * Called on the background scan saver, after base scan content is saved
     * but before DriveBackupScheduler.onScanSaved(). No image is silently
     * substituted by a GL screenshot.
     */
    fun finishAndWrite(
        context: Context,
        identity: ScanFieldRecorder.RecordIdentity,
        writer: (String,String,File) -> Unit
    ) {
        val c=synchronized(lock) {
            val result=sessions.remove(key(identity))
            if (active===result) active=null
            result?.closed=true
            result
        } ?: return
        // Do not unregister the next scan's sensors when its predecessor
        // is still being written on a background save thread.
        val noActive=synchronized(lock) { active == null }
        if (noActive) sensorManager?.unregisterListener(listener)
        // Serial executor barrier; an image's worker always finishes first.
        try { io.submit { }.get(20,TimeUnit.SECONDS) }
        catch (_:Exception) { synchronized(lock) { c.errors++ } }
        val frames:List<String>
        val imu:List<String>
        val summary:String
        synchronized(lock) {
            frames=c.rows.sortedBy { it.substringBefore(",").toIntOrNull() ?: 0 }
            imu=c.imu.toList()
            summary="{\"schema_version\":1,\"kind\":\"RGB_RESEARCH_ONLY\"," +
                "\"slope_certified\":false,\"frame_attempts\":" + c.acquired +
                ",\"jpeg_saved\":" + c.saved +
                ",\"cpu_image_unavailable\":" + c.unavailable +
                ",\"dropped_busy\":" + c.droppedBusy +
                ",\"dropped_crop_or_format\":" + c.droppedCrop +
                ",\"errors\":" + c.errors + "}"
        }
        val csv=File(c.dir,"rgb_frames.csv")
        csv.writeText(
            "index,ar_frame_timestamp_ns,cpu_image_timestamp_ns,android_camera_timestamp_ns," +
            "width,height,fx,fy,cx,cy,intrinsic_width,intrinsic_height," +
            "camera_tx,camera_ty,camera_tz,camera_qx,camera_qy,camera_qz,camera_qw," +
            "sensor_tx,sensor_ty,sensor_tz,sensor_qx,sensor_qy,sensor_qz,sensor_qw," +
            "ball_world_x,ball_world_y,ball_world_z," +
            "cup_world_x,cup_world_y,cup_world_z,tracking\n" +
            frames.joinToString("\n",postfix=if (frames.isEmpty()) "" else "\n")
        )
        val imuFile=File(c.dir,"rgb_imu.csv")
        imuFile.writeText("sensor_timestamp_ns,callback_elapsed_ns,type,x,y,z,accuracy\n" +
            imu.joinToString("\n",postfix=if (imu.isEmpty()) "" else "\n"))
        val status=File(c.dir,"rgb_capture_status.json")
        status.writeText(summary)
        val images=c.dir.listFiles()?.filter { it.name.matches(Regex("rgb_[0-9]{4}\\.jpg")) }
            ?.sortedBy { it.name } ?: emptyList()
        val export=images + listOf(csv,imuFile,status)
        var complete=true
        for (f in export) {
            try { writer(f.name,if(f.name.endsWith(".jpg")) "image/jpeg"
                else if(f.name.endsWith(".csv")) "text/csv"
                else "application/json",f) }
            catch (_:Exception) { complete=false }
        }
        if (complete) c.dir.deleteRecursively()
        // On error keep the temp capture in app cache for forensic recovery.
    }
}
