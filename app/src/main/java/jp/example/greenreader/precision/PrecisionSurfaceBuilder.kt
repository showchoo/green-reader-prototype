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
object PrecisionSurfaceBuilder {
    @Volatile var lastDiagnostic: String = ""
        private set

    @Volatile var tuningMinObservations: Int = 2
    @Volatile var tuningMaxMadMeters: Float = 0.040f
    @Volatile var tuningBaseHeightBandMeters: Float = 0.10f
    @Volatile var tuningMaxExpectedGrade: Float = 0.08f
    @Volatile var tuningNeighborReach: Int = 3
    @Volatile var tuningStepBaseMeters: Float = 0.045f
    @Volatile var tuningMedianToleranceMeters: Float = 0.050f
    @Volatile var tuningLocalMinNeighbors: Int = 2

    fun resetTuning() {
        tuningMinObservations = 2
        tuningMaxMadMeters = 0.040f
        tuningBaseHeightBandMeters = 0.10f
        tuningMaxExpectedGrade = 0.08f
        tuningNeighborReach = 3
        tuningStepBaseMeters = 0.045f
        tuningMedianToleranceMeters = 0.050f
        tuningLocalMinNeighbors = 2
    }

    fun tuningSummary(): String =
        "obs=$tuningMinObservations mad=" + String.format("%.3f", tuningMaxMadMeters) +
        " band=" + String.format("%.2f", tuningBaseHeightBandMeters) +
        " grade=" + String.format("%.2f", tuningMaxExpectedGrade) +
        " reach=$tuningNeighborReach step=" + String.format("%.3f", tuningStepBaseMeters) +
        " med=" + String.format("%.3f", tuningMedianToleranceMeters) +
        " nbr=$tuningLocalMinNeighbors"
    private data class Key(val x: Int, val z: Int)
    private data class Sample(val h: Float, val c: Float, val frame: Long)
    private data class Candidate(val key: Key, val cell: PrecisionSurfaceCell)
    private data class StableCell(val key: Key, val med: Float, val mad: Float, val confidence: Float, val observations: Int)

    fun build(
        points: List<PrecisionDepthPoint>,
        voxelSizeMeters: Float = 0.05f,
        minObservations: Int = tuningMinObservations,
        maxMadMeters: Float = tuningMaxMadMeters,
        maxExpectedGrade: Float = tuningMaxExpectedGrade
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

        // Stage 1a: temporal stability + robust height estimate in each X/Z voxel.
        // Do NOT assume the ARCore ball-anchor Y is exactly the physical turf height.
        // On some devices the hit-test anchor and depth cloud can have a persistent
        // vertical offset even though both are otherwise geometrically correct.
        var rejectObservations = 0
        var rejectMad = 0
        var rejectHeight = 0
        val stable = ArrayList<StableCell>()
        for ((key, values) in buckets) {
            val unique = values.mapTo(HashSet()) { it.frame }.size
            if (unique < minObservations) { rejectObservations++; continue }

            val heights = values.map { it.h }.sorted()
            val med = median(heights)
            val deviations = heights.map { abs(it - med) }.sorted()
            val mad = median(deviations)
            if (!med.isFinite() || !mad.isFinite() || mad > maxMadMeters) { rejectMad++; continue }

            stable += StableCell(
                key = key,
                med = med,
                mad = mad,
                confidence = values.map { it.c }.average().toFloat(),
                observations = unique
            )
        }

        // Stage 1b: estimate the actual turf reference height from stable cells close
        // to the ball. A robust median makes a constant ARCore anchor/depth Y offset
        // harmless while still rejecting distant geometry.
        // Estimate the dominant horizontal surface from the full stable-cell
        // height distribution. This avoids assuming that valid depth exists within
        // 1 m of the ball anchor, which is not true on every ARCore device/view.
        val heightBinSize = 0.05f
        val heightBins = HashMap<Int, MutableList<Float>>()
        for (sc in stable) {
            if (!sc.med.isFinite()) continue
            val bin = floor(sc.med / heightBinSize).toInt()
            heightBins.getOrPut(bin) { ArrayList() }.add(sc.med)
        }
        val dominantBin = heightBins.maxByOrNull { it.value.size }?.key
        val dominantHeights = if (dominantBin != null) {
            stable.mapNotNull { sc ->
                if (abs(sc.med - (dominantBin + 0.5f) * heightBinSize) <= 0.10f) sc.med else null
            }.sorted()
        } else emptyList()
        val groundReference = median(dominantHeights)

        val initial = ArrayList<Candidate>()
        if (groundReference.isFinite()) {
            for (sc in stable) {
                val x = (sc.key.x + 0.5f) * voxelSizeMeters
                val z = (sc.key.z + 0.5f) * voxelSizeMeters
                val radius = hypot(x.toDouble(), z.toDouble()).toFloat()

                // Accept realistic grade around the observed turf reference rather
                // than around an assumed exact anchor Y=0.
                val allowedHeight = tuningBaseHeightBandMeters + maxExpectedGrade * radius
                if (abs(sc.med - groundReference) > allowedHeight) { rejectHeight++; continue }

                initial += Candidate(
                    sc.key,
                    PrecisionSurfaceCell(
                        x = x,
                        z = z,
                        height = sc.med,
                        confidence = sc.confidence,
                        observations = sc.observations,
                        madMeters = sc.mad
                    )
                )
            }
        } else {
            rejectHeight = stable.size
        }

        val refText = if (groundReference.isFinite()) String.format("%.3f", groundReference) else "nan"
        val minRadius = stable.minOfOrNull { hypot(((it.key.x + 0.5f) * voxelSizeMeters).toDouble(), ((it.key.z + 0.5f) * voxelSizeMeters).toDouble()).toFloat() }
        val maxRadius = stable.maxOfOrNull { hypot(((it.key.x + 0.5f) * voxelSizeMeters).toDouble(), ((it.key.z + 0.5f) * voxelSizeMeters).toDouble()).toFloat() }
        val radiusText = if (minRadius != null && maxRadius != null) String.format("%.2f..%.2f", minRadius, maxRadius) else "nan"
        val stage1Diagnostic = "buckets=${buckets.size} obsReject=$rejectObservations madReject=$rejectMad heightReject=$rejectHeight stable=${stable.size} ref=$refText refN=${dominantHeights.size} radius=$radiusText stage1=${initial.size}"

        if (initial.isEmpty()) {
            lastDiagnostic = "$stage1Diagnostic seed=0 connected=0 median=0"
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
            .filter { abs(it.cell.height - groundReference) <= 0.14f }
            .sortedWith(
                compareBy<Candidate> {
                    hypot(it.cell.x.toDouble(), it.cell.z.toDouble())
                }.thenBy {
                    abs(it.cell.height - groundReference)
                }
            )
            .take(16)
            .map { it.key }

        // If no ground can be established near the ball, fail closed. Falling back
        // to arbitrary distant geometry is exactly what produced the huge false slopes.
        if (seedKeys.isEmpty()) {
            lastDiagnostic = "$stage1Diagnostic seed=0 connected=0 median=0"
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

            for (dx in -tuningNeighborReach..tuningNeighborReach) {
                for (dz in -tuningNeighborReach..tuningNeighborReach) {
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
                    val allowedStep = tuningStepBaseMeters + 0.15f * horizontal
                    if (abs(next.height - current.height) <= allowedStep) {
                        accepted += nextKey
                        queue.addLast(nextKey)
                    }
                }
            }
        }

        val connectedGround = accepted.mapNotNull { map[it]?.cell }
        var ground = connectedGround

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
            if (neighborHeights.size < tuningLocalMinNeighbors) return@filter false
            val localMedian = median(neighborHeights.sorted())
            abs(cell.height - localMedian) <= tuningMedianToleranceMeters
        }

        val medianCount = ground.size
        var usedConnectedFallback = false
        if (ground.size < 25 && connectedGround.size >= 25) {
            ground = connectedGround
            usedConnectedFallback = true
        }

        lastDiagnostic = "$stage1Diagnostic seed=${seedKeys.size} connected=${connectedGround.size} median=$medianCount fallback=${if (usedConnectedFallback) 1 else 0} final=${ground.size} tune=[" + tuningSummary() + "]"

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
