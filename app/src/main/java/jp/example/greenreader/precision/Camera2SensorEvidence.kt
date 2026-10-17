package jp.example.greenreader.precision

import java.util.Locale

/**
 * Bounded, append-only research IMU trace. Runs on the same HandlerThread as
 * Camera2 image callbacks. The trace is evidence, NOT a physical orientation
 * estimate, and can never approve putting-line grade.
 *
 * SensorEvent.timestamp is the sensor's monotonic timestamp. Record
 * elapsedRealtimeNanos at callback time separately to audit delivery latency.
 */
class Camera2SensorEvidence(private val perTypeLimit:Int = 3600) {
    companion object {
        const val GRAVITY = "gravity"
        const val ACCELEROMETER = "accelerometer"
        const val GYROSCOPE = "gyroscope"
        const val GYROSCOPE_UNCALIBRATED = "gyroscope_uncalibrated"
        const val CSV_HEADER =
            "sensor_type,sensor_timestamp_ns,callback_elapsed_ns,"+
            "x,y,z,bias_x,bias_y,bias_z,accuracy"
        val TYPES = listOf(GRAVITY, ACCELEROMETER, GYROSCOPE, GYROSCOPE_UNCALIBRATED)
    }
    private val rows = ArrayList<String>()
    private val counts = LinkedHashMap<String,Int>()
    private val dropped = LinkedHashMap<String,Int>()
    private val outOfOrder = LinkedHashMap<String,Int>()
    private val lastTime = LinkedHashMap<String,Long>()
    var firstCallbackElapsedNs:Long? = null
        private set
    var lastCallbackElapsedNs:Long? = null
        private set

    init {
        require(perTypeLimit in 1..12000) { "Per-sensor cap must be bounded" }
        TYPES.forEach {
            counts[it]=0
            dropped[it]=0
            outOfOrder[it]=0
        }
    }

    fun add(
        type:String,
        sensorTimestampNs:Long,
        callbackElapsedNs:Long,
        values:FloatArray,
        accuracy:Int
    ):Boolean {
        if(type !in TYPES || sensorTimestampNs<=0L ||
            callbackElapsedNs<=0L || values.size<3 ||
            !values.take(3).all { it.isFinite() })return false
        // Preserve validity of the gyroscope-with-bias format.
        if(type==GYROSCOPE_UNCALIBRATED &&
            (values.size<6 || !values.take(6).all { it.isFinite() }))return false
        val last=lastTime[type]
        if(last!=null && sensorTimestampNs<=last) {
            outOfOrder[type]=(outOfOrder[type]?:0)+1
            return false
        }
        if((counts[type]?:0)>=perTypeLimit) {
            dropped[type]=(dropped[type]?:0)+1
            return false
        }
        fun fmt(v:Float)=String.format(Locale.US,"%.8f",v.toDouble())
        val extras=if(type==GYROSCOPE_UNCALIBRATED)
            (3..5).map { fmt(values[it]) } else listOf("","","")
        rows.add(listOf(type,sensorTimestampNs.toString(),
            callbackElapsedNs.toString(),
            fmt(values[0]),fmt(values[1]),fmt(values[2]),
            extras[0],extras[1],extras[2],accuracy.toString()).joinToString(","))
        counts[type]=(counts[type]?:0)+1
        lastTime[type]=sensorTimestampNs
        if(firstCallbackElapsedNs==null)firstCallbackElapsedNs=callbackElapsedNs
        lastCallbackElapsedNs=callbackElapsedNs
        return true
    }

    fun csv():String = CSV_HEADER+"\n"+
        rows.joinToString("\n",postfix=if(rows.isEmpty()) "" else "\n")
    fun sampleCounts():Map<String,Int> = counts.toMap()
    fun droppedCounts():Map<String,Int> = dropped.toMap()
    fun outOfOrderCounts():Map<String,Int> = outOfOrder.toMap()
}
