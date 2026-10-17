package jp.example.greenreader

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureFailure
import android.media.ImageReader
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import jp.example.greenreader.field.Camera2DepthArchive
import jp.example.greenreader.precision.PrecisionDepth16Codec
import jp.example.greenreader.precision.Camera2SensorEvidence
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteOrder
import java.util.Locale

/**
 * Separate research-only DEPTH16 activity: MainActivity's ARCore is paused
 * before opening Camera2; depthIsExclusive=true forbids simultaneous RGB.
 * No ToF hardware identity or putting-slope accuracy is claimed.
 */
class Camera2DepthCaptureActivity:AppCompatActivity() {
    companion object {
        private const val MAX_FRAMES=12
        private const val WATCHDOG_MS=15000L
        private const val START_DELAY_MS=900L
    }
    private lateinit var status:TextView
    private lateinit var button:Button
    private lateinit var backgroundThread:HandlerThread
    private lateinit var worker:Handler
    private val ui=Handler(android.os.Looper.getMainLooper())
    private var device:CameraDevice?=null
    private var captureSession:CameraCaptureSession?=null
    private var reader:ImageReader?=null
    private var started=false
    @Volatile private var finishing=false
    @Volatile private var finalized=false
    private var errorCount=0
    private var firstError=""
    private var frameCount=0
    private var cameraId=""
    private var width=0
    private var height=0
    private var calibration="{}"
    private val savedFrames=ArrayList<File>()
    private val records=ArrayList<String>()
    private val gravities=ArrayList<String>()
    private val sensorEvidence=Camera2SensorEvidence()
    private val requestedSensors=linkedMapOf<String,Boolean>()
    private val registeredSensors=linkedMapOf<String,Boolean>()
    private var cameraTimestampSource:Int?=null
    private var sensorStartElapsedNs:Long?=null
    private lateinit var temporaryDir:File
    private lateinit var manager:CameraManager
    private var sensorManager:SensorManager?=null
    private val listener=object:SensorEventListener {
        override fun onAccuracyChanged(sensor:Sensor?,accuracy:Int){}
        override fun onSensorChanged(event:SensorEvent) {
            if(finishing || event.values.size<3)return
            val kind=when(event.sensor.type) {
                Sensor.TYPE_GRAVITY -> Camera2SensorEvidence.GRAVITY
                Sensor.TYPE_ACCELEROMETER -> Camera2SensorEvidence.ACCELEROMETER
                Sensor.TYPE_GYROSCOPE -> Camera2SensorEvidence.GYROSCOPE
                Sensor.TYPE_GYROSCOPE_UNCALIBRATED ->
                    Camera2SensorEvidence.GYROSCOPE_UNCALIBRATED
                else -> return
            }
            val callbackNs=SystemClock.elapsedRealtimeNanos()
            sensorEvidence.add(kind,event.timestamp,callbackNs,
                event.values,event.accuracy)
            // Legacy v11.0 file is preserved, with unchanged columns/order.
            if(kind==Camera2SensorEvidence.GRAVITY && gravities.size<3000) {
                val v=event.values
                gravities.add(event.timestamp.toString()+","+
                    callbackNs+","+
                    String.format(Locale.US,"%.7f,%.7f,%.7f",v[0],v[1],v[2])+
                    ","+event.accuracy)
            }
        }
    }

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        val layout=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setPadding(24,40,24,24)
        }
        layout.addView(TextView(this).apply {
            text="Camera2 深度カメラ（研究専用）"
            textSize=20f
        })
        status=TextView(this).apply {
            textSize=16f
            text="背面カメラを床に向けてから開始してください。\n"+
                "数秒間、ほぼ静止したままDEPTH16画像を記録します。\n"+
                "まだ傾斜精度は保証されていません。"
            setPadding(0,30,0,30)
        }
        layout.addView(status)
        button=Button(this).apply {
            text="深度データ取得開始"
            setOnClickListener {
                if(!started) beginCapture()
                else if(finalized) finish()
                else requestFinish("user_stop")
            }
        }
        layout.addView(button)
        setContentView(layout)
        temporaryDir=File(cacheDir,"tof_research_"+System.currentTimeMillis())
            .apply {mkdirs()}
        manager=getSystemService(CAMERA_SERVICE) as CameraManager
        backgroundThread=HandlerThread("GreenReader-Camera2-Depth").apply {start()}
        worker=Handler(backgroundThread.looper)
        sensorManager=getSystemService(SENSOR_SERVICE) as SensorManager
    }

    private fun setStatus(text:String)=ui.post {
        if(!isFinishing && !isDestroyed)status.text=text
    }
    private fun recordError(message:String) {
        errorCount++
        if(firstError.isBlank())firstError=message.take(200)
    }

    private fun beginCapture() {
        if(started)return
        started=true
        button.text="取得を終了して保存"
        if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED) {
            recordError("CAMERA_PERMISSION_NOT_GRANTED")
            requestFinish("permission_denied")
            return
        }
        setStatus("ARCoreがカメラを解放するまで準備しています…")
        worker.post { registerResearchSensors() }
        ui.postDelayed({if(!finishing)requestFinish("watchdog_timeout")},WATCHDOG_MS)
        ui.postDelayed({if(!finishing)worker.post {openCamera()}},START_DELAY_MS)
    }

    private fun registerResearchSensors() {
        // Register before Camera2 opening so early filter convergence is visible.
        sensorStartElapsedNs=SystemClock.elapsedRealtimeNanos()
        val requirements=listOf(
            Sensor.TYPE_GRAVITY to Camera2SensorEvidence.GRAVITY,
            Sensor.TYPE_ACCELEROMETER to Camera2SensorEvidence.ACCELEROMETER,
            Sensor.TYPE_GYROSCOPE to Camera2SensorEvidence.GYROSCOPE,
            Sensor.TYPE_GYROSCOPE_UNCALIBRATED to
                Camera2SensorEvidence.GYROSCOPE_UNCALIBRATED
        )
        for((type,name) in requirements) {
            val sensor=sensorManager?.getDefaultSensor(type)
            requestedSensors[name]=sensor!=null
            val registered=if(sensor!=null) {
                try {
                    sensorManager?.registerListener(
                        listener,sensor,SensorManager.SENSOR_DELAY_GAME,worker)==true
                } catch(_:Exception) { false }
            } else false
            registeredSensors[name]=registered
        }
    }

    private fun getCalibration(
        id:String,c:CameraCharacteristics,w:Int,h:Int
    ):String {
        fun floats(arr:FloatArray?):JSONArray=JSONArray().apply {
            arr?.forEach {put(if(it.isFinite())it.toDouble() else JSONObject.NULL)}
        }
        return JSONObject()
            .put("schema_version",1).put("camera_id",id)
            .put("width",w).put("height",h)
            .put("format","DEPTH16_LE_U16_ROW_MAJOR")
            .put("range_unit","millimeters")
            .put("lens_intrinsic_calibration",
                floats(c.get(CameraCharacteristics.LENS_INTRINSIC_CALIBRATION)))
            .put("lens_distortion",
                floats(c.get(CameraCharacteristics.LENS_DISTORTION)))
            .put("lens_pose_translation",
                floats(c.get(CameraCharacteristics.LENS_POSE_TRANSLATION)))
            .put("lens_pose_rotation",
                floats(c.get(CameraCharacteristics.LENS_POSE_ROTATION)))
            .put("lens_pose_reference",
                c.get(CameraCharacteristics.LENS_POSE_REFERENCE))
            .put("sensor_orientation_degrees",
                c.get(CameraCharacteristics.SENSOR_ORIENTATION))
            .put("sensor_timestamp_source",
                c.get(CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE))
            .put("depth_is_exclusive",
                c.get(CameraCharacteristics.DEPTH_DEPTH_IS_EXCLUSIVE))
            .put("tof_hardware_identity_verified",false)
            .put("grade_accuracy_certified",false).toString(2)
    }

    private fun openCamera() {
        if(finishing)return
        try {
            val options=manager.cameraIdList.mapNotNull { id ->
                try {
                    val c=manager.getCameraCharacteristics(id)
                    val advertised=c.get(
                        CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)
                        ?.contains(CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT)
                        ?:false
                    val sizes=c.get(
                        CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                        ?.getOutputSizes(ImageFormat.DEPTH16)
                    if(!advertised || sizes.isNullOrEmpty())null
                    else Triple(id,c,sizes)
                } catch(e:Exception) {
                    recordError("characteristics_"+id+"_"+e.javaClass.simpleName)
                    null
                }
            }
            if(options.isEmpty()) {
                recordError("No public Camera2 DEPTH16")
                requestFinish("no_camera2_depth16")
                return
            }
            val selected=options.maxByOrNull {
                it.third.maxOf {size->size.width.toLong()*size.height}
            }!!
            cameraId=selected.first
            // Keep initial test bounded and recoverable if a vendor advertises
            // an unexpectedly huge depth stream.
            val size=selected.third.filter { it.width<=640 && it.height<=480 }
                .maxByOrNull { it.width*it.height }
                ?:selected.third.minByOrNull {it.width*it.height}!!
            width=size.width
            height=size.height
            calibration=getCalibration(cameraId,selected.second,width,height)
            cameraTimestampSource=selected.second.get(
                CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE)
            reader=ImageReader.newInstance(width,height,ImageFormat.DEPTH16,2)
                .also {r->r.setOnImageAvailableListener({onImage(it = r)},worker)}
            setStatus("DEPTH16カメラ ID "+cameraId+" ("+width+"×"+height+
                ") を開いています…")
            manager.openCamera(cameraId,object:CameraDevice.StateCallback() {
                override fun onOpened(camera:CameraDevice) {
                    if(finishing) {camera.close();return}
                    device=camera
                    configureSession(camera)
                }
                override fun onDisconnected(camera:CameraDevice) {
                    recordError("camera_onDisconnected")
                    camera.close()
                    requestFinish("camera_disconnected")
                }
                override fun onError(camera:CameraDevice,error:Int) {
                    recordError("camera_onError_"+error)
                    camera.close()
                    requestFinish("camera_error")
                }
            },worker)
        } catch(e:Exception) {
            recordError("open_"+e.javaClass.simpleName+":"+(e.message?:""))
            requestFinish("open_failed")
        }
    }

    private fun configureSession(camera:CameraDevice) {
        try {
            val target=reader?.surface ?:error("Missing ImageReader")
            camera.createCaptureSession(listOf(target),
                object:CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session:CameraCaptureSession) {
                        if(finishing) {session.close();return}
                        captureSession=session
                        try {
                            val request=try {
                                camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW)
                            } catch (_:Exception) {
                                camera.createCaptureRequest(
                                    CameraDevice.TEMPLATE_STILL_CAPTURE)
                            }
                            request.addTarget(target)
                            session.setRepeatingRequest(request.build(),
                                object:CameraCaptureSession.CaptureCallback() {
                                    override fun onCaptureFailed(
                                        session:CameraCaptureSession,
                                        request:CaptureRequest,
                                        failure:CaptureFailure
                                    ) {
                                        if(!finishing)recordError(
                                            "capture_failed_"+failure.reason)
                                    }
                                },worker)
                            setStatus("深度画像を収集中。床を映したまま静止してください。")
                        } catch(e:Exception) {
                            recordError("repeat_"+e.javaClass.simpleName)
                            requestFinish("repeating_failed")
                        }
                    }
                    override fun onConfigureFailed(session:CameraCaptureSession) {
                        recordError("configure_failed")
                        requestFinish("configure_failed")
                    }
                },worker)
        } catch(e:Exception) {
            recordError("session_"+e.javaClass.simpleName)
            requestFinish("session_failed")
        }
    }

    private fun onImage(it:ImageReader) {
        if(finishing)return
        val img=try{it.acquireLatestImage()}
            catch(e:Exception) {
                recordError("acquire_"+e.javaClass.simpleName)
                return
            } ?:return
        img.use {image ->
            if(finishing || frameCount>=MAX_FRAMES)return
            try {
                if(image.format!=ImageFormat.DEPTH16 ||
                    image.width!=width || image.height!=height ||
                    image.planes.size!=1)
                    error("Unexpected DEPTH16 geometry")
                val raw=PrecisionDepth16Codec.copyPacked(
                    image.planes[0].buffer,width,height,
                    image.planes[0].rowStride,
                    image.planes[0].pixelStride,ByteOrder.nativeOrder())
                val stats=PrecisionDepth16Codec.summary(raw,width,height)
                val next=frameCount+1
                val path=File(temporaryDir,
                    "depth_"+String.format(Locale.US,"%04d",next)+".bin")
                path.writeBytes(raw)
                savedFrames.add(path)
                frameCount=next
                records.add(
                    next.toString()+","+image.timestamp+","+width+","+height+","+
                    stats.validPixels+","+stats.confidentPixels+","+
                    (stats.minMillimeters?.toString()?:"")+","+
                    (stats.medianMillimeters?.toString()?:"")+","+
                    (stats.maxMillimeters?.toString()?:"")+","+
                    String.format(Locale.US,"%.6f,%.6f",
                        stats.coverage,stats.confidentCoverage)+","+
                    SystemClock.elapsedRealtimeNanos())
                setStatus("DEPTH16 "+frameCount+"/"+MAX_FRAMES+
                    " 保存。距離の有効画素 "+String.format(Locale.US,"%.1f%%",
                        stats.coverage*100)+", 中央値 "+
                    (stats.medianMillimeters?.toString()?:"—")+"mm")
                if(frameCount>=MAX_FRAMES)requestFinish("max_frames")
            } catch(e:Throwable) {
                recordError("frame_"+e.javaClass.simpleName+":"+(e.message?:""))
            }
        }
    }

    private fun requestFinish(reason:String) {
        if(finishing)return
        finishing=true
        ui.removeCallbacksAndMessages(null)
        setStatus("深度カメラを閉じて、データを保存しています…")
        worker.post {
            try{captureSession?.stopRepeating()}catch (_:Exception){}
            try{captureSession?.abortCaptures()}catch (_:Exception){}
            try{captureSession?.close()}catch (_:Exception){}
            try{device?.close()}catch (_:Exception){}
            try{reader?.close()}catch (_:Exception){}
            try{sensorManager?.unregisterListener(listener)}catch (_:Exception){}
            captureSession=null;device=null;reader=null
            val data=savedFrames.toList()
            val frameCsv="index,image_timestamp_ns,width,height,valid_pixels,"+
                "confident_pixels,min_mm,median_mm,max_mm,coverage,"+
                "confident_coverage,callback_elapsed_ns\n"+
                records.joinToString("\n",postfix=if(records.isEmpty())"" else "\n")
            val gravityCsv="sensor_timestamp_ns,callback_elapsed_ns,"+
                "gx,gy,gz,accuracy\n"+
                gravities.joinToString("\n",
                    postfix=if(gravities.isEmpty())"" else "\n")
            val sensorCsv=sensorEvidence.csv()
            val sensorMetadata=JSONObject()
                .put("schema_version",1)
                .put("kind","CAMERA2_DIRECT_DEPTH_IMU_DIAGNOSTICS")
                .put("requested_sensor_available",JSONObject(requestedSensors.toMap()))
                .put("sensor_listener_registered",JSONObject(registeredSensors.toMap()))
                .put("per_sensor_sample_count",JSONObject(sensorEvidence.sampleCounts()))
                .put("per_sensor_cap_dropped",JSONObject(sensorEvidence.droppedCounts()))
                .put("per_sensor_out_of_order_dropped",
                    JSONObject(sensorEvidence.outOfOrderCounts()))
                .put("register_start_elapsed_ns",sensorStartElapsedNs)
                .put("first_sensor_callback_elapsed_ns",
                    sensorEvidence.firstCallbackElapsedNs)
                .put("last_sensor_callback_elapsed_ns",
                    sensorEvidence.lastCallbackElapsedNs)
                .put("camera_timestamp_source",cameraTimestampSource)
                .put("camera_vs_sensor_timestamp_comparable",
                    cameraTimestampSource==
                        CameraMetadata.SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME)
                .put("physical_camera_motion_certified",false)
                .put("absolute_grade_accuracy_certified",false)
                .put("note","Sensor timestamps are monotonic. Camera timestamp"+
                    " comparability requires Camera2 REALTIME; gyro/accel do not"+
                    " independently prove world-frame orientation.").toString(2)
            val summary=JSONObject()
                .put("schema_version",2)
                .put("kind","CAMERA2_DEPTH16_DIRECT_CAPTURE")
                .put("raw_imu_evidence_saved",true)
                .put("physical_gravity_reference_verified",false)
                .put("camera_id",cameraId)
                .put("width",width).put("height",height)
                .put("frame_count",frameCount)
                .put("error_count",errorCount)
                .put("first_error",firstError)
                .put("stop_reason",reason)
                .put("slope_accuracy_certified",false)
                .put("tof_hardware_identity_verified",false).toString(2)
            Thread {
                try {
                    val dest=Camera2DepthArchive.save(
                        applicationContext,calibration,data,frameCsv,
                        gravityCsv,summary,sensorCsv,sensorMetadata)
                    val counts=sensorEvidence.sampleCounts()
                    val imuStatus="加速度 "+
                        (counts[Camera2SensorEvidence.ACCELEROMETER]?:0)+
                        "件 / ジャイロ "+
                        (counts[Camera2SensorEvidence.GYROSCOPE]?:0)+
                        "件 / 重力 "+
                        (counts[Camera2SensorEvidence.GRAVITY]?:0)+"件"
                    ui.post {
                        finalized=true
                        if(!isFinishing && !isDestroyed) {
                            status.text="DEPTH16取得結果を保存しました。\n"+
                                "フレーム "+frameCount+" / "+MAX_FRAMES+
                                " / エラー "+errorCount+"件\n"+
                                imuStatus+"\n"+
                                "保存先: "+dest.savedFolder+
                                "\n既存のDrive自動保存がONなら同期します。\n"+
                                "距離精度・ToF実体は未検証です。"
                            button.text="アプリへ戻る"
                        }
                    }
                    temporaryDir.deleteRecursively()
                } catch(e:Throwable) {
                    ui.post {
                        finalized=true
                        if(!isFinishing && !isDestroyed) {
                            status.text="保存エラー: "+e.javaClass.simpleName+
                                " "+(e.message?:"")
                            button.text="アプリへ戻る"
                        }
                    }
                }
            }.start()
        }
    }

    override fun onDestroy() {
        if(!finishing)requestFinish("activity_destroyed")
        if(::backgroundThread.isInitialized)backgroundThread.quitSafely()
        super.onDestroy()
    }
}
