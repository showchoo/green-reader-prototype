package jp.example.greenreader.precision

import java.nio.ByteBuffer
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class PrecisionYuv420Nv21Test {
    @Test fun planarFourByFourSupportsPaddedRows() {
        val width=4
        val height=4
        val y=ByteArray(6*4)
        for (row in 0 until 4) for (x in 0 until 4)
            y[row*6+x]=(10+row*4+x).toByte()
        val u=ByteArray(3*2)
        val v=ByteArray(3*2)
        u[0]=11;u[1]=12;u[3]=13;u[4]=14
        v[0]=21;v[1]=22;v[3]=23;v[4]=24
        val actual=PrecisionYuv420Nv21.pack(4,4,
            ByteBuffer.wrap(y),6,1,ByteBuffer.wrap(u),3,1,
            ByteBuffer.wrap(v),3,1)
        val expected=(10..25).map { it.toByte() } +
            listOf(21,11,22,12,23,13,24,14).map { it.toByte() }
        assertArrayEquals(expected.toByteArray(),actual)
    }

    @Test fun chromaPixelStrideTwoIsUsedCorrectly() {
        val y=ByteBuffer.wrap(byteArrayOf(1,2,3,4,5,6,7,8,
                                         9,10,11,12,13,14,15,16))
        val u=ByteBuffer.wrap(byteArrayOf(50,0,51,0,52,0,53,0))
        val v=ByteBuffer.wrap(byteArrayOf(70,0,71,0,72,0,73,0))
        val packed=PrecisionYuv420Nv21.pack(4,4,y,4,1,u,4,2,v,4,2)
        assertEquals(24,packed.size)
        assertArrayEquals(byteArrayOf(70,50,71,51,72,52,73,53),
            packed.copyOfRange(16,24))
    }

    @Test fun lumaPixelStrideTwoIsUsedCorrectly() {
        val y=ByteBuffer.wrap(byteArrayOf(1,0,2,0,3,0,4,0,
                                          5,0,6,0,7,0,8,0))
        val u=ByteBuffer.wrap(byteArrayOf(10,11))
        val v=ByteBuffer.wrap(byteArrayOf(20,21))
        val packed=PrecisionYuv420Nv21.pack(4,2,y,8,2,u,2,1,v,2,1)
        assertArrayEquals(byteArrayOf(1,2,3,4,5,6,7,8,20,10,21,11),packed)
    }

    @Test fun invalidOddDimensionsAreRejected() {
        val src=ByteBuffer.wrap(ByteArray(100))
        assertThrows(IllegalArgumentException::class.java) {
            PrecisionYuv420Nv21.pack(5,4,src,5,1,src,3,1,src,3,1)
        }
    }
}
