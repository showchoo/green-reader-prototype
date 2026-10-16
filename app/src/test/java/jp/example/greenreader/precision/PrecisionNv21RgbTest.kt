package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertThrows
import org.junit.Test

class PrecisionNv21RgbTest {
    private fun rgbAt(bytes: ByteArray, w:Int=2,h:Int=2): Int =
        PrecisionNv21Rgb.convert(bytes,w,h).pixels[0]

    @Test fun blackAndWhiteNeutralChroma() {
        val black=byteArrayOf(16,16,16,16,128.toByte(),128.toByte())
        val white=byteArrayOf(235.toByte(),235.toByte(),
            235.toByte(),235.toByte(),128.toByte(),128.toByte())
        assertEquals(0xff000000.toInt(),rgbAt(black))
        assertEquals(0xffffffff.toInt(),rgbAt(white))
    }

    @Test fun redsAndBluesUseNv21VuOrder() {
        // Rec. 601 limited-range samples for vivid red and blue.
        val red=byteArrayOf(82,82,82,82,240.toByte(),90.toByte())
        val blue=byteArrayOf(41,41,41,41,110,240.toByte())
        val r=rgbAt(red)
        val b=rgbAt(blue)
        assertTrue(((r ushr 16) and 255) > 220)
        assertTrue(((r ushr 0) and 255) < 35)
        assertTrue(((b ushr 0) and 255) > 220)
        assertTrue(((b ushr 16) and 255) < 35)
    }

    @Test fun conversionRespectsResolutionLimitWithoutCrop() {
        val w=1600
        val h=1200
        val yuv=ByteArray(w*h*3/2) { if(it < w*h) 128.toByte()
            else 128.toByte() }
        val res=PrecisionNv21Rgb.convert(yuv,w,h,640)
        assertEquals(640,res.width)
        assertEquals(480,res.height)
        assertEquals(640*480,res.pixels.size)
    }

    @Test fun smallFramePreservesFullResolution() {
        val yuv=ByteArray(8*8*3/2) { 128.toByte() }
        val res=PrecisionNv21Rgb.convert(yuv,8,8,1280)
        assertEquals(8,res.width)
        assertEquals(8,res.height)
        assertEquals(64,res.pixels.size)
    }

    @Test fun shortImageIsRejected() {
        assertThrows(IllegalArgumentException::class.java) {
            PrecisionNv21Rgb.convert(ByteArray(2),4,4)
        }
    }
}
