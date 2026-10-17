package jp.example.greenreader.precision

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.roundToInt

/**
 * Camera2 DEPTH16 raw packed format, per Android ImageFormat.DEPTH16.
 *
 * Bits 0..12: radial distance in millimetres (0 = unknown).
 * Bits 13..15: confidence code (0 = 100%, 1 = 0%, 2..7 = (code-1)/7).
 * The return byte stream is row-major LITTLE_ENDIAN packed U16, independent
 * of the camera Image.Plane rowStride and pixelStride. No height/grade inferred.
 */
object PrecisionDepth16Codec {
    data class Summary(
        val width: Int,
        val height: Int,
        val validPixels: Int,
        val confidentPixels: Int,
        val minMillimeters: Int?,
        val medianMillimeters: Int?,
        val maxMillimeters: Int?,
        val invalidPixels: Int,
        val invalidConfidencePixels: Int,
        val coverage: Double,
        val confidentCoverage: Double
    )

    fun rangeMm(packed: Int) = packed and 0x1fff
    fun confidenceCode(packed: Int) = (packed ushr 13) and 7
    fun confidence(code: Int): Double {
        require(code in 0..7)
        return if (code == 0) 1.0 else (code - 1) / 7.0
    }

    fun copyPacked(
        plane: ByteBuffer, width: Int, height: Int,
        rowStride: Int, pixelStride: Int,
        order: ByteOrder = ByteOrder.nativeOrder()
    ): ByteArray {
        require(width > 0 && height > 0 && width <= 4096 && height <= 4096)
        require(rowStride >= 2 && pixelStride >= 2)
        val end = (height - 1).toLong() * rowStride +
            (width - 1).toLong() * pixelStride + 2L
        val src = plane.duplicate().order(order)
        require(end <= src.limit().toLong()) { "DEPTH16 row/stride outside buffer" }
        val output = ByteArray(width * height * 2)
        var dest = 0
        for (y in 0 until height) {
            val start = y * rowStride
            for (x in 0 until width) {
                val packed = src.getShort(start + x * pixelStride).toInt() and 0xffff
                output[dest++] = (packed and 255).toByte()
                output[dest++] = (packed ushr 8).toByte()
            }
        }
        return output
    }

    fun summary(data: ByteArray, width: Int, height: Int): Summary {
        require(width > 0 && height > 0 && data.size == width * height * 2)
        val millimeters = IntArray(width * height)
        var valid = 0
        var confident = 0
        var invalidConfidence = 0
        var min = Int.MAX_VALUE
        var max = Int.MIN_VALUE
        for (i in 0 until width * height) {
            val packed = (data[i*2].toInt() and 255) or
                ((data[i*2+1].toInt() and 255) shl 8)
            val mm=rangeMm(packed)
            val c=confidenceCode(packed)
            if (mm == 0) continue
            if (c == 1) invalidConfidence++
            millimeters[valid++]=mm
            if (confidence(c)>=0.5)confident++
            if (mm<min)min=mm
            if (mm>max)max=mm
        }
        millimeters.sort(0,valid)
        val median=if(valid==0)null else
            if(valid%2==1)millimeters[valid/2]
            else (millimeters[valid/2-1]+millimeters[valid/2])/2
        val total=width*height
        return Summary(width,height,valid,confident,
            if(valid>0)min else null,median,
            if(valid>0)max else null,total-valid,invalidConfidence,
            valid.toDouble()/total,confident.toDouble()/total)
    }
}
