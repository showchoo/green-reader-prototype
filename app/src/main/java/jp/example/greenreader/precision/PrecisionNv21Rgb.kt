package jp.example.greenreader.precision

import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Deterministic software fallback for ARCore YUV_420_888 camera frames, after
 * stride-safe packing to NV21. Pure Kotlin, independently unit-testable.
 *
 * Camera JPEG output is intentionally bounded to <=1280 pixels wide so the
 * Bitmap/encoder runs on a single background worker without exploding memory.
 * Store both source and encoded dimensions in RGB metadata: calibrated camera
 * intrinsics belong to the ORIGINAL source pixels unless rescaled.
 */
object PrecisionNv21Rgb {
    data class Result(
        val width: Int,
        val height: Int,
        val pixels: IntArray
    )

    private fun clamp8(v: Int): Int = when {
        v < 0 -> 0
        v > 255 -> 255
        else -> v
    }

    fun convert(nv21: ByteArray, width: Int, height: Int,
                maxOutputWidth: Int = 1280): Result {
        require(width > 0 && height > 0 && width % 2 == 0 && height % 2 == 0)
        require(maxOutputWidth >= 2)
        require(width.toLong() * height.toLong() * 3L / 2L <= Int.MAX_VALUE)
        require(nv21.size >= width * height * 3 / 2)

        val outW = if (width <= maxOutputWidth) width
            else ((maxOutputWidth.coerceAtMost(width)) / 2) * 2
        val outH = if (outW == width) height
            else ((height.toDouble() * outW / width).roundToInt() / 2 * 2)
                .coerceAtLeast(2)
        val argb = IntArray(outW * outH)
        val chromaStart = width * height
        for (row in 0 until outH) {
            // Select centre of the source pixel footprint (nearest neighbour).
            val yy = (((row + 0.5) * height / outH).toInt())
                .coerceIn(0, height - 1)
            for (col in 0 until outW) {
                val xx = (((col + 0.5) * width / outW).toInt())
                    .coerceIn(0, width - 1)
                val y = (nv21[yy * width + xx].toInt() and 0xff) - 16
                val vu = chromaStart + (yy / 2) * width + (xx / 2) * 2
                val v = (nv21[vu].toInt() and 0xff) - 128
                val u = (nv21[vu + 1].toInt() and 0xff) - 128
                val c = y.coerceAtLeast(0)
                val red = clamp8((298 * c + 409 * v + 128) shr 8)
                val green = clamp8((298 * c - 100 * u - 208 * v + 128) shr 8)
                val blue = clamp8((298 * c + 516 * u + 128) shr 8)
                argb[row * outW + col] = (0xff shl 24) or
                    (red shl 16) or (green shl 8) or blue
            }
        }
        return Result(outW, outH, argb)
    }
}
