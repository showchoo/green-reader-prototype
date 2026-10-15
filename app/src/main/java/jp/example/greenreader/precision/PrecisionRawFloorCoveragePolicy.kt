package jp.example.greenreader.precision

import kotlin.math.abs
import kotlin.math.hypot

/**
 * Checks spatial and near-marker support of the already accepted Raw points,
 * independently of the number of pixels passing confidence threshold.
 *
 * A dense cloud on a wall, shoe or a small corner of the image MUST NOT
 * suppress Full Depth supplementation. This is conservative acquisition
 * engineering, not a proof that the observed floor is physically level.
 *
 * Coordinates are gravity-aligned and ball-relative. The ball's local
 * position is the origin, and cup coordinates come from its ARCore anchor.
 */
object PrecisionRawFloorCoveragePolicy {
    private const val BINS = 5
    private const val MIN_NEAR_BALL = 5
    private const val MIN_CANDIDATE_POINTS = 24
    private const val MAX_MARKER_VERTICAL_DELTA_M = 0.20f
    private const val MAX_CROSS_TRACK_M = 0.28f

    data class Evidence(
        val valid: Boolean,
        val reason: String,
        val acceptedRawPoints: Int,
        val corridorPoints: Int,
        val nearBallPoints: Int,
        val coveredBins: Int,
        val puttLengthM: Float
    ) {
        fun diagnostic(): String =
            "RAW_FLOOR_COVERAGE_V1 valid=" + valid +
            " reason=" + reason +
            " raw=" + acceptedRawPoints +
            " corridor=" + corridorPoints +
            " nearBall=" + nearBallPoints +
            " bins=" + coveredBins + "/" + BINS +
            " baselineM=" + String.format(java.util.Locale.US,"%.2f",puttLengthM) +
            " groundTruth=false"
    }

    fun evaluate(
        rawPointsFromThisFrame: List<PrecisionDepthPoint>,
        cupLocal: FloatArray?
    ): Evidence {
        val n = rawPointsFromThisFrame.size
        if (cupLocal == null || cupLocal.size < 3 ||
            !cupLocal[0].isFinite() || !cupLocal[1].isFinite() ||
            !cupLocal[2].isFinite()) {
            return Evidence(false,"NO_VALID_CUP_MARKER",n,0,0,0,Float.NaN)
        }
        val length = hypot(cupLocal[0],cupLocal[2])
        if (!length.isFinite() || length < 0.40f || length > 12f) {
            return Evidence(false,"UNSUPPORTED_PUTT_LENGTH",n,0,0,0,length)
        }
        if (n < MIN_CANDIDATE_POINTS) {
            return Evidence(false,"TOO_FEW_RAW_POINTS",n,0,0,0,length)
        }
        val forwardX = cupLocal[0]/length
        val forwardZ = cupLocal[2]/length
        val bins = BooleanArray(BINS)
        var corridor = 0
        var nearBall = 0

        for (p in rawPointsFromThisFrame) {
            if (p.depthSource != "raw" ||
                !p.x.isFinite() || !p.y.isFinite() || !p.z.isFinite()) continue
            val along = p.x*forwardX+p.z*forwardZ
            val lateral = abs(-p.x*forwardZ+p.z*forwardX)
            // Check a broad plausible near-marker envelope; never force the
            // floor to 0% or correct a legitimate putt grade numerically.
            // ARCore marker heights themselves are NOT ground truth.
            val expectedY = (along/length).coerceIn(0f,1f)*cupLocal[1]
            if (abs(p.y-expectedY) > MAX_MARKER_VERTICAL_DELTA_M ||
                lateral > MAX_CROSS_TRACK_M ||
                along < -0.15f || along > length+0.15f) continue
            corridor++
            if (hypot(p.x,p.z) <= 0.25f) nearBall++
            if (along in 0f..length) {
                val slot = (along/length*BINS).toInt().coerceIn(0,BINS-1)
                bins[slot] = true
            }
        }
        val covered = bins.count { it }
        val requiredBins = if (length <= 0.65f) 2 else 3
        val reason = when {
            corridor < MIN_CANDIDATE_POINTS -> "CORRIDOR_SPARSE"
            nearBall < MIN_NEAR_BALL -> "NO_NEAR_BALL_SUPPORT"
            covered < requiredBins -> "INSUFFICIENT_SPATIAL_SPAN"
            else -> "CANDIDATE_COVERAGE_PRESENT"
        }
        return Evidence(reason == "CANDIDATE_COVERAGE_PRESENT",
            reason,n,corridor,nearBall,covered,length)
    }
}
