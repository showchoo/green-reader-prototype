package jp.example.greenreader.precision

import kotlin.math.abs
import kotlin.math.floor

object PrecisionSurfaceBuilder {
    private data class Key(val x: Int, val z: Int)
    private data class Sample(val h: Float, val c: Float, val frame: Long)

    fun build(
        points: List<PrecisionDepthPoint>,
        voxelSizeMeters: Float = 0.05f,
        minObservations: Int = 3,
        maxMadMeters: Float = 0.035f
    ): PrecisionSurfaceModel {
        val buckets = HashMap<Key, MutableList<Sample>>()
        val frames = HashSet<Long>()
        for (p in points) {
            val key = Key(
                floor(p.x / voxelSizeMeters).toInt(),
                floor(p.z / voxelSizeMeters).toInt()
            )
            buckets.getOrPut(key) { ArrayList() }.add(Sample(p.y, p.confidence, p.frameTimestampNs))
            frames += p.frameTimestampNs
        }

        val cells = ArrayList<PrecisionSurfaceCell>()
        for ((key, values) in buckets) {
            val unique = values.mapTo(HashSet()) { it.frame }.size
            if (unique < minObservations) continue
            val heights = values.map { it.h }.sorted()
            val med = median(heights)
            val deviations = heights.map { abs(it - med) }.sorted()
            val mad = median(deviations)
            if (mad > maxMadMeters) continue
            val meanConf = values.map { it.c }.average().toFloat()
            cells += PrecisionSurfaceCell(
                x = (key.x + 0.5f) * voxelSizeMeters,
                z = (key.z + 0.5f) * voxelSizeMeters,
                height = med,
                confidence = meanConf,
                observations = unique,
                madMeters = mad
            )
        }
        return PrecisionSurfaceModel(cells, voxelSizeMeters, points.size, frames.size)
    }

    private fun median(sorted: List<Float>): Float {
        if (sorted.isEmpty()) return Float.NaN
        val m = sorted.size / 2
        return if (sorted.size % 2 == 1) sorted[m] else (sorted[m - 1] + sorted[m]) * 0.5f
    }
}
