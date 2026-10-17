package jp.example.greenreader.precision

import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class PrecisionDepth16CodecTest {
    private fun raw(mm:Int, confidenceCode:Int):Int =
        (mm and 0x1fff) or ((confidenceCode and 7) shl 13)

    @Test fun confidenceSemanticsFromAndroidContract() {
        assertEquals(1.0,PrecisionDepth16Codec.confidence(0),1e-9)
        assertEquals(0.0,PrecisionDepth16Codec.confidence(1),1e-9)
        assertEquals(1.0/7,PrecisionDepth16Codec.confidence(2),1e-9)
        assertEquals(1.0,PrecisionDepth16Codec.confidence(0),1e-9)
        assertEquals(6.0/7,PrecisionDepth16Codec.confidence(7),1e-9)
    }

    @Test fun packedRangeAndConfidenceSeparated() {
        for (c in 0..7) {
            val raw=raw(2540,c)
            assertEquals(2540,PrecisionDepth16Codec.rangeMm(raw))
            assertEquals(c,PrecisionDepth16Codec.confidenceCode(raw))
        }
    }

    @Test fun stridePaddedBufferIsDecodedInByteOrderWithoutPadding() {
        val bb=ByteBuffer.allocate(18).order(ByteOrder.LITTLE_ENDIAN)
        val samples=intArrayOf(raw(1100,0),raw(1400,7),raw(900,1),raw(2300,2))
        bb.putShort(0,samples[0].toShort())
        bb.putShort(4,samples[1].toShort())
        bb.putShort(10,samples[2].toShort())
        bb.putShort(14,samples[3].toShort())
        val bytes=PrecisionDepth16Codec.copyPacked(bb,2,2,10,4,ByteOrder.LITTLE_ENDIAN)
        assertEquals(8,bytes.size)
        val out=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        for (i in 0..3)assertEquals(samples[i],out.getShort(i*2).toInt() and 65535)
        val summary=PrecisionDepth16Codec.summary(bytes,2,2)
        assertEquals(4,summary.validPixels)
        assertEquals(2,summary.confidentPixels)
        assertEquals(1,summary.invalidConfidencePixels)
        assertEquals(1250,summary.medianMillimeters)
        assertEquals(900,summary.minMillimeters)
        assertEquals(2300,summary.maxMillimeters)
    }

    @Test fun invalidZeroRangesDoNotCountAsValid() {
        val bytes=ByteArray(2*2*2)
        val summary=PrecisionDepth16Codec.summary(bytes,2,2)
        assertEquals(0,summary.validPixels)
        assertNull(summary.medianMillimeters)
        assertEquals(0.0,summary.coverage,0.0)
    }

    @Test fun shortRowBufferRejectedBeforeAnyOutOfBoundsAccess() {
        assertThrows(IllegalArgumentException::class.java) {
            PrecisionDepth16Codec.copyPacked(
                ByteBuffer.wrap(ByteArray(3)),2,2,4,2,ByteOrder.LITTLE_ENDIAN)
        }
    }

    @Test fun incorrectEndianIsDetectable() {
        val b=ByteBuffer.allocate(2).order(ByteOrder.BIG_ENDIAN)
        b.putShort(0,raw(1000,0).toShort())
        val bytes=PrecisionDepth16Codec.copyPacked(
            b,1,1,2,2,ByteOrder.BIG_ENDIAN)
        assertArrayEquals(byteArrayOf(0xe8.toByte(),0x03),bytes)
    }
}
