package jp.example.greenreader.precision

import java.nio.ByteBuffer

/**
 * Exact YUV_420_888 -> NV21 packing, honoring independent plane row/pixel
 * strides (including chroma pixelStride=2). No RGB/depth geometry inference.
 *
 * Pure JVM-compatible helper so padded layout can be regression-tested.
 */
object PrecisionYuv420Nv21 {
    fun pack(
        width: Int,
        height: Int,
        yBuffer: ByteBuffer, yRowStride: Int, yPixelStride: Int,
        uBuffer: ByteBuffer, uRowStride: Int, uPixelStride: Int,
        vBuffer: ByteBuffer, vRowStride: Int, vPixelStride: Int
    ): ByteArray {
        require(width > 0 && height > 0 && width % 2 == 0 && height % 2 == 0)
        require(yRowStride > 0 && yPixelStride > 0 &&
            uRowStride > 0 && uPixelStride > 0 &&
            vRowStride > 0 && vPixelStride > 0)
        val y=yBuffer.duplicate()
        val u=uBuffer.duplicate()
        val v=vBuffer.duplicate()
        val output=ByteArray(width*height*3/2)
        var offset=0
        for (row in 0 until height) {
            val start = row*yRowStride
            for (col in 0 until width) {
                output[offset++]=y.get(start+col*yPixelStride)
            }
        }
        for (row in 0 until height/2) {
            val uBase=row*uRowStride
            val vBase=row*vRowStride
            for (col in 0 until width/2) {
                // NV21 is VU interleaved, NOT UV.
                output[offset++]=v.get(vBase+col*vPixelStride)
                output[offset++]=u.get(uBase+col*uPixelStride)
            }
        }
        return output
    }
}
