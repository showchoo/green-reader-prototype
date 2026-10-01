from pathlib import Path

depth = Path("app/src/main/java/jp/example/greenreader/analysis/DepthCollector.kt")
main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")

depth.write_text(r'''package jp.example.greenreader.analysis

import com.google.ar.core.Coordinates2d
import com.google.ar.core.Frame
import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.NotYetAvailableException
import java.nio.ByteOrder
import kotlin.math.max

class DepthCollector {
    private val points = ArrayList<Vec3>(30000)

    @Synchronized fun clear() = points.clear()
    @Synchronized fun size(): Int = points.size
    @Synchronized fun snapshot(): List<Vec3> = points.toList()

    /**
     * Integrate depth into a gravity-aligned, anchor-relative frame.
     *
     * Important: never apply the ball Anchor's pitch/roll to the accumulated
     * cloud. Those components come from the hit-test/plane pose and can rotate a
     * physically flat floor into a steep local slope. We follow anchor position
     * and yaw only via [GravityAlignedFrame].
     */
    @Synchronized
    fun integrate(
        frame: Frame,
        referencePose: Pose,
        pixelStrideStep: Int = 6,
        minDepthM: Float = 0.25f,
        maxDepthM: Float = 8f
    ) {
        val camera = frame.camera
        if (camera.trackingState != TrackingState.TRACKING) return
        try {
            frame.acquireDepthImage16Bits().use { img ->
                val plane = img.planes[0]
                val buf = plane.buffer.order(ByteOrder.LITTLE_ENDIAN)
                val pStride = plane.pixelStride
                val rStride = plane.rowStride
                val intr = camera.imageIntrinsics
                val focal = intr.focalLength
                val principal = intr.principalPoint
                val dims = intr.imageDimensions
                val cameraPose = camera.pose
                val levelFrame = GravityAlignedFrame.fromPose(referencePose)

                val step = max(2, pixelStrideStep)
                val sampleCapacity = ((img.width + step - 1) / step) * ((img.height + step - 1) / step)
                val textureCoords = FloatArray(sampleCapacity * 2)
                val depths = FloatArray(sampleCapacity)
                var sampleCount = 0

                for (y in 0 until img.height step step) {
                    for (x in 0 until img.width step step) {
                        val idx = y * rStride + x * pStride
                        if (idx + 1 >= buf.limit()) continue
                        val mm = java.lang.Short.toUnsignedInt(buf.getShort(idx))
                        if (mm == 0) continue
                        val z = mm / 1000f
                        if (z < minDepthM || z > maxDepthM) continue

                        val out = sampleCount * 2
                        textureCoords[out] = (x + 0.5f) / img.width.toFloat()
                        textureCoords[out + 1] = (y + 0.5f) / img.height.toFloat()
                        depths[sampleCount] = z
                        sampleCount++
                    }
                }
                if (sampleCount == 0) return@use

                val imageCoords = FloatArray(sampleCount * 2)
                frame.transformCoordinates2d(
                    Coordinates2d.TEXTURE_NORMALIZED,
                    textureCoords.copyOf(sampleCount * 2),
                    Coordinates2d.IMAGE_PIXELS,
                    imageCoords
                )

                val imageW = dims[0].toFloat()
                val imageH = dims[1].toFloat()
                for (i in 0 until sampleCount) {
                    val u = imageCoords[i * 2]
                    val v = imageCoords[i * 2 + 1]
                    if (!u.isFinite() || !v.isFinite()) continue
                    if (u < 0f || v < 0f || u >= imageW || v >= imageH) continue

                    val z = depths[i]
                    val cx = (u - principal[0]) / focal[0] * z
                    val cy = -(v - principal[1]) / focal[1] * z
                    val world = cameraPose.transformPoint(floatArrayOf(cx, cy, -z))
                    val local = levelFrame.worldToLocal(world)
                    points += Vec3(local[0], local[1], local[2])
                }

                if (points.size > 70000) {
                    points.subList(0, points.size - 50000).clear()
                }
            }
        } catch (_: NotYetAvailableException) {
        }
    }
}
''', encoding="utf-8")

s = main.read_text(encoding="utf-8")

old_marks = '''    /**
     * Ball/cup positions in the persistent ball-Anchor coordinate frame.
     * DepthCollector stores every frame in exactly this frame as well.
     */
    private fun currentAnalysisMarks(): Pair<Vec3, Vec3>? {
        val bAnchor = ballAnchor ?: return null
        val cAnchor = cupAnchor ?: return null
        if (bAnchor.trackingState != TrackingState.TRACKING ||
            cAnchor.trackingState != TrackingState.TRACKING) return null
        val worldToBall = bAnchor.pose.inverse()
        val bt = worldToBall.transformPoint(bAnchor.pose.translation)
        val ct = worldToBall.transformPoint(cAnchor.pose.translation)
        return Vec3(bt[0], bt[1], bt[2]) to Vec3(ct[0], ct[1], ct[2])
    }
'''
new_marks = '''    /**
     * Ball/cup positions in a gravity-aligned ball-Anchor frame.
     *
     * We intentionally keep world Y as vertical and remove Anchor pitch/roll.
     * This prevents hit-test plane orientation error from appearing as green slope.
     */
    private fun currentAnalysisMarks(): Pair<Vec3, Vec3>? {
        val bAnchor = ballAnchor ?: return null
        val cAnchor = cupAnchor ?: return null
        if (bAnchor.trackingState != TrackingState.TRACKING ||
            cAnchor.trackingState != TrackingState.TRACKING) return null
        val levelFrame = GravityAlignedFrame.fromPose(bAnchor.pose)
        val bt = levelFrame.worldToLocal(bAnchor.pose.translation)
        val ct = levelFrame.worldToLocal(cAnchor.pose.translation)
        return Vec3(bt[0], bt[1], bt[2]) to Vec3(ct[0], ct[1], ct[2])
    }
'''
if old_marks not in s:
    raise SystemExit("currentAnalysisMarks block not found")
s = s.replace(old_marks, new_marks, 1)

old_projection = '''        val midWorldRaw = referencePose.transformPoint(midLocal)
        val sideWorldRaw = referencePose.transformPoint(sideLocal)
'''
new_projection = '''        val levelFrame = GravityAlignedFrame.fromPose(referencePose)
        val midWorldRaw = levelFrame.localToWorld(midLocal)
        val sideWorldRaw = levelFrame.localToWorld(sideLocal)
'''
if old_projection not in s:
    raise SystemExit("cross projection block not found")
s = s.replace(old_projection, new_projection, 1)

s = s.replace(
    'appVersion = "Precision 1.3"',
    'appVersion = "Precision 1.4"'
)

main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 130', 'versionCode = 140')
b = b.replace('versionName = "1.3"', 'versionName = "1.4"')
build.write_text(b, encoding="utf-8")

print("Applied gravity-aligned analysis frame for Precision v1.4")
