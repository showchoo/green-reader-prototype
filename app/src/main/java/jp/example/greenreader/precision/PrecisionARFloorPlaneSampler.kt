package jp.example.greenreader.precision

import com.google.ar.core.Frame
import com.google.ar.core.Plane
import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import jp.example.greenreader.analysis.GravityAlignedFrame
import kotlin.math.abs

/**
 * Observes ARCore's CHANGED horizontal plane estimates on each tracked
 * camera frame. Frame.getUpdatedTrackables may return zero when a perfectly
 * valid plane already existed. That case is explicitly reported as absent.
 *
 * No known plane is assumed to be a surveyed or calibrated horizontal floor.
 */
class PrecisionARFloorPlaneSampler {
    private var updated = 0
    private var nearBall = 0
    private var bestScore = Float.POSITIVE_INFINITY
    private var best: PrecisionGroundPlaneBiasAudit.PlaneObservation? = null

    fun clear() {
        updated = 0
        nearBall = 0
        bestScore = Float.POSITIVE_INFINITY
        best = null
    }

    fun observe(frame: Frame, ball: Pose) {
        val local = GravityAlignedFrame.fromPose(ball)
        for (plane in frame.getUpdatedTrackables(Plane::class.java)) {
            if (plane.trackingState != TrackingState.TRACKING ||
                plane.type != Plane.Type.HORIZONTAL_UPWARD_FACING ||
                plane.subsumedBy != null) continue
            updated++
            val center = plane.centerPose
            val centerLocal = local.worldToLocal(center.translation)
            val normalWorld = center.rotateVector(floatArrayOf(0f, 1f, 0f))
            val tip = local.worldToLocal(floatArrayOf(
                ball.tx() + normalWorld[0],
                ball.ty() + normalWorld[1],
                ball.tz() + normalWorld[2]
            ))
            val nx=tip[0]; val ny=tip[1]; val nz=tip[2]
            if (!nx.isFinite() || !ny.isFinite() || !nz.isFinite() ||
                abs(ny) < 0.8f) continue

            val heightAtBall = centerLocal[1] +
                (nx*centerLocal[0] + nz*centerLocal[2]) / ny
            if (!heightAtBall.isFinite() || abs(heightAtBall) > 0.35f) continue
            nearBall++
            val containsMarker = try { plane.isPoseInExtents(ball) }
                catch (_: Throwable) { false }
            val score = abs(heightAtBall) +
                (if (containsMarker) 0f else 0.08f)
            if (score < bestScore) {
                bestScore = score
                best = PrecisionGroundPlaneBiasAudit.PlaneObservation(
                    available=true,
                    slopeXPct=-100f*nx/ny,
                    slopeZPct=-100f*nz/ny,
                    heightAtBallM=heightAtBall,
                    markerInsideExtents=containsMarker
                )
            }
        }
    }

    fun snapshot(): PrecisionGroundPlaneBiasAudit.PlaneObservation {
        val observed = best
        return if (observed == null)
            PrecisionGroundPlaneBiasAudit.PlaneObservation(
                planeUpdates=updated,trackedNearBallUpdates=nearBall
            )
        else observed.copy(
            planeUpdates=updated,trackedNearBallUpdates=nearBall
        )
    }
}
