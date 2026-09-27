package jp.example.greenreader.precision

import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max

/**
 * Builds a surface from repeated Raw Depth samples while aggressively rejecting
 * non-ground geometry (walls, furniture edges, isolated returns).
 *
 * The coordinate frame is gravity-aligned and ball-relative, so y ~= 0 is the
 * expected ground height at the ball.
 */
object PrecisionSurfaceBuilder {\n    @Volatile var lastDiagnostic: String = ""\n        private set
    private data class Key(val x: Int, val z: Int)
    private data class Sample(val h: Float, val c: Float, val frame: Long)
    private data class Candidate(val key: Key, val cell: PrecisionSurfaceCell)

    fun build(
        points: List<PrecisionDepthPoint>,
        voxelSizeMeters: Float = 0.05f,
        minObservations: Int = 2,
        maxMadMeters: Float = 0.040f,
        maxExpectedGrade: Float = 0.08f
    ): PrecisionSurfaceModel {
        if (points.isEmpty()) {
            return PrecisionSurfaceModel(emptyList(), voxelSizeMeters, 0, 0)
        }

        val buckets = HashMap<Key, MutableList<Sample>>()
        val frames = HashSet<Long>()
        for (p in points) {
            val key = Key(
                floor(p.x / voxelSizeMeters).toInt(),
                floor(p.z / voxelSizeMeters).toInt()
            )
            buckets.getOrPut(key) { ArrayList() }
                .add(Sample(p.y, p.confidence, p.frameTimestampNs))
            frames += p.frameTimestampNs
        }

        // Stage 1: temporal stability + robust height estimate in each X/Z voxel.
        var rejectObservations = 0\n        var rejectMad = 0\n        var rejectHeight = 0\n        val initial = ArrayList<Candidate>()
        for ((key, values) in buckets) {
            val unique = values.mapTo(HashSet()) { it.frame }.size
            if (unique < minObservations) { rejectObservations++; continue }

            val heights = values.map { it.h }.sorted()
            val med = median(heights)
            val deviations = heights.map { abs(it - med) }.sorted()
            val mad = median(deviations)
            if (!med.isFinite() || !mad.isFinite() || mad > maxMadMeters) { rejectMad++; continue }

            val x = (key.x + 0.5f) * voxelSizeMeters
            val z = (key.z + 0.5f) * voxelSizeMeters
            val radius = hypot(x.toDouble(), z.toDouble()).toFloat()

            // Ball-relative ground must remain in a physically plausible height band.
            // Allows up to 8% true grade plus 7 cm of ARCore zero-height uncertainty.
            val allowedHeight = 0.07f + maxExpectedGrade * radius
            if (abs(med) > allowedHeight) { rejectHeight++; continue }

            val meanConf = values.map { it.c }.average().toFloat()
            initial += Candidate(
                key,
                PrecisionSurfaceCell(
                    x = x,
                    z = z,
                    height = med,
                    confidence = meanConf,
                    observations = unique,
                    madMeters = mad
                )
            )
        }

        val stage1Diagnostic = "buckets=${buckets.size} obsReject=$rejectObservations madReject=$rejectMad heightReject=$rejectHeight stage1=${initial.size}"\n\n        if (initial.isEmpty()) {\n            lastDiagnostic = "$stage1Diagnostic seed=0 connected=0 median=0"
            return PrecisionSurfaceModel(
                cells = emptyList(),
                voxelSizeMeters = voxelSizeMeters,
                sourcePointCount = points.size,
                uniqueFrames = frames.size,
                candidateCellCount = 0,
                rejectedCellCount = buckets.size,
                groundCellCount = 0
            )
        }

        val map = initial.associateBy { it.key }

        // Stage 2: find seed ground close to the ball. This prevents a wall or table
        // elsewhere in the image becoming the dominant connected surface.
        val seedKeys = initial
            .filter {
                hypot(it.cell.x.toDouble(), it.cell.z.toDouble()) <= 0.80 &&
                    abs(it.cell.height) <= 0.14f
            }
            .sortedBy { abs(it.cell.height) }
            .take(16)
            .map { it.key }

        // If no ground can be established near the ball, fail closed. Falling back
        // to arbitrary distant geometry is exactly what produced the huge false slopes.
        if (seedKeys.isEmpty()) {\n            lastDiagnostic = "$stage1Diagnostic seed=0 connected=0 median=0"
            return PrecisionSurfaceModel(
                cells = emptyList(),
                voxelSizeMeters = voxelSizeMeters,
                sourcePointCount = points.size,
                uniqueFrames = frames.size,
                candidateCellCount = initial.size,
                rejectedCellCount = initial.size,
                groundCellCount = 0
            )
        }

        // Stage 3: flood-fill only a height-continuous connected surface.
        // Search up to 2 voxels away to tolerate sparse Raw Depth.
        val accepted = LinkedHashSet<Key>()
        val queue = ArrayDeque<Key>()
        seedKeys.forEach {
            if (accepted.add(it)) queue.addLast(it)
        }

        while (queue.isNotEmpty()) {
            val currentKey = queue.removeFirst()
            val current = map[currentKey]?.cell ?: continue

            for (dx in -2..2) {
                for (dz in -2..2) {
                    if (dx == 0 && dz == 0) continue
                    val nextKey = Key(currentKey.x + dx, currentKey.z + dz)
                    if (accepted.contains(nextKey)) continue
                    val next = map[nextKey]?.cell ?: continue

                    val horizontal = hypot(
                        ((nextKey.x - currentKey.x) * voxelSizeMeters).toDouble(),
                        ((nextKey.z - currentKey.z) * voxelSizeMeters).toDouble()
                    ).toFloat()

                    // Real putting surfaces change height gradually. 2 cm baseline
                    // tolerance plus 12% over the gap still allows steep greens but
                    // rejects vertical walls/furniture edges.
                    val allowedStep = 0.035f + 0.15f * horizontal
                    if (abs(next.height - current.height) <= allowedStep) {
                        accepted += nextKey
                        queue.addLast(nextKey)
                    }
                }
            }
        }

        var ground = accepted.mapNotNull { map[it]?.cell }

        // Stage 4: local median consistency. Removes isolated spikes that happen to
        // connect through one noisy cell.
        val acceptedMap = accepted.associateWith { map[it]!!.cell }
        ground = ground.filter { cell ->
            val kx = floor(cell.x / voxelSizeMeters).toInt()
            val kz = floor(cell.z / voxelSizeMeters).toInt()
            val neighborHeights = ArrayList<Float>()
            for (dx in -3..3) {
                for (dz in -3..3) {
                    acceptedMap[Key(kx + dx, kz + dz)]?.let { neighborHeights += it.height }
                }
            }
            if (neighborHeights.size < 3) return@filter false
            val localMedian = median(neighborHeights.sorted())
            abs(cell.height - localMedian) <= 0.040f
        }

        return PrecisionSurfaceModel(
            cells = ground,
            voxelSizeMeters = voxelSizeMeters,
            sourcePointCount = points.size,
            uniqueFrames = frames.size,
            candidateCellCount = initial.size,
            rejectedCellCount = max(0, initial.size - ground.size),
            groundCellCount = ground.size
        )
    }

    private fun median(sorted: List<Float>): Float {
        if (sorted.isEmpty()) return Float.NaN
        val m = sorted.size / 2
        return if (sorted.size % 2 == 1) sorted[m]
        else (sorted[m - 1] + sorted[m]) * 0.5f
    }
}
