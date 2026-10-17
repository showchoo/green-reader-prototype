package jp.example.greenreader.precision

import org.junit.Assert.*
import org.junit.Test

class Camera2SensorEvidenceTest {
    @Test fun timestampAndAllSensorAxesRemainInCsv() {
        val trace=Camera2SensorEvidence()
        assertTrue(trace.add(Camera2SensorEvidence.GRAVITY,1000,1030,
            floatArrayOf(0.1f,0.2f,9.8f),3))
        assertTrue(trace.add(Camera2SensorEvidence.ACCELEROMETER,1040,1070,
            floatArrayOf(0.1f,0.3f,9.7f),3))
        assertTrue(trace.add(Camera2SensorEvidence.GYROSCOPE,1080,1110,
            floatArrayOf(.01f,.02f,-.03f),3))
        assertTrue(trace.add(Camera2SensorEvidence.GYROSCOPE_UNCALIBRATED,
            1100,1120,floatArrayOf(1f,2f,3f,.1f,.2f,.3f),2))
        val s=trace.csv()
        assertTrue(s.startsWith(Camera2SensorEvidence.CSV_HEADER))
        assertEquals(5,s.trimEnd().lines().size)
        assertTrue(s.contains("gyroscope_uncalibrated,1100,1120"))
        assertTrue(s.contains("0.10000000,0.20000000,0.30000001"))
        assertEquals(4,trace.sampleCounts().values.sum())
        assertEquals(1030L,trace.firstCallbackElapsedNs)
        assertEquals(1120L,trace.lastCallbackElapsedNs)
    }

    @Test fun outOfOrderSensorCallbacksFailClosed() {
        val trace=Camera2SensorEvidence()
        assertTrue(trace.add("gravity",100,150,floatArrayOf(0f,0f,9f),3))
        assertFalse(trace.add("gravity",100,151,floatArrayOf(0f,0f,9f),3))
        assertFalse(trace.add("gravity",90,160,floatArrayOf(0f,0f,9f),3))
        assertEquals(1,trace.sampleCounts()["gravity"])
        assertEquals(2,trace.outOfOrderCounts()["gravity"])
    }

    @Test fun overflowIsCountedWithoutUnboundedStorage() {
        val trace=Camera2SensorEvidence(1)
        assertTrue(trace.add("gyroscope",100,120,floatArrayOf(0f,0f,0f),3))
        assertFalse(trace.add("gyroscope",101,121,floatArrayOf(0f,0f,0f),3))
        assertEquals(1,trace.sampleCounts()["gyroscope"])
        assertEquals(1,trace.droppedCounts()["gyroscope"])
        assertEquals(2,trace.csv().trimEnd().lines().size)
    }

    @Test fun invalidDataAndMalformedUncalibratedGyroAreRejected() {
        val trace=Camera2SensorEvidence()
        assertFalse(trace.add("accelerometer",0,5,floatArrayOf(1f,2f,3f),2))
        assertFalse(trace.add("accelerometer",3,5,floatArrayOf(Float.NaN,0f,0f),2))
        assertFalse(trace.add("gyroscope_uncalibrated",4,6,floatArrayOf(1f,2f,3f),2))
        assertFalse(trace.add("unknown",5,7,floatArrayOf(1f,2f,3f),2))
        assertEquals(1,trace.csv().trimEnd().lines().size)
    }
}
