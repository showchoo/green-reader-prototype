"""v10.4: diagnostic-only texture-intrinsics vs CPU-image projection audit.

ARCore official Raw Depth reconstruction uses scaled texture intrinsics.
Existing Full Depth reconstruction maps texture to CPU IMAGE_PIXELS.
Compare both paths with exactly the same z and camera pose, at a bounded
number of pixels per accepted Depth frame, across Raw and Full sources.
Do NOT alter active geometry, point selection, slopes, freshness or quality.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
collector=root/"precision/PrecisionDepthCollector.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
c=collector.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(s,old,new,label):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"v10.4 {label}: expected exactly 1, found {n}")
    return s.replace(old,new,1)

c=one(c,
'''    private val arFloorPlaneSampler = PrecisionARFloorPlaneSampler()''',
'''    private val arFloorPlaneSampler = PrecisionARFloorPlaneSampler()
    private val projectionRayAudit = PrecisionProjectionRayAudit.Buffer()''',
"audit buffer")
c=one(c,
'''        arFloorPlaneSampler.clear()
        frameTimestamps.clear()''',
'''        arFloorPlaneSampler.clear()
        projectionRayAudit.clear()
        frameTimestamps.clear()''',
"per-window reset")
c=one(c,
'''                samples, arFloorPlaneSampler.snapshot()
            )''',
'''                samples, arFloorPlaneSampler.snapshot()
            ) + "\\n" +
            projectionRayAudit.diagnostic()''',
"persist projection comparison in existing collector diagnostics")

helper = r'''    /**
     * Bounded independent diagnostic; never feeds live production point cloud.
     *
     * Full Depth and Raw Depth use different projection models in the v10.3
     * pipeline. For the same depth pixel, compare the two resulting world
     * points and record the discrepancy versus camera pitch. This comparison
     * does NOT prove that either model measures the actual floor correctly.
     */
    private fun observeProjectionRayAudit(
        frame: Frame,
        depth: Image,
        xs: IntArray,
        ys: IntArray,
        zs: FloatArray,
        count: Int,
        fx: Float,
        fy: Float,
        cx: Float,
        cy: Float,
        isRaw: Boolean
    ) {
        val source = if (isRaw) "raw" else "full"
        try {
            val camera = frame.camera
            val imageIntr = camera.imageIntrinsics
            val imageFocal = imageIntr.focalLength
            val imagePrincipal = imageIntr.principalPoint
            val imageDims = imageIntr.imageDimensions
            if (count <= 0 || imageFocal[0] <= 0f ||
                imageFocal[1] <= 0f) return

            // Never take more than 48 calibration probes from one image.
            val sampleN = count.coerceAtMost(48)
            val coords = FloatArray(sampleN * 2)
            val indices = IntArray(sampleN)
            for (i in 0 until sampleN) {
                val at = i * count / sampleN
                indices[i] = at
                coords[i * 2] = (xs[at] + 0.5f) / depth.width.toFloat()
                coords[i * 2 + 1] = (ys[at] + 0.5f) / depth.height.toFloat()
            }
            val mapped = FloatArray(sampleN * 2)
            frame.transformCoordinates2d(
                Coordinates2d.TEXTURE_NORMALIZED,
                coords,
                Coordinates2d.IMAGE_PIXELS,
                mapped
            )
            val forward = camera.pose.rotateVector(floatArrayOf(0f, 0f, -1f))
            val pitchDeg = Math.toDegrees(kotlin.math.atan2(
                forward[1].toDouble(),
                kotlin.math.hypot(forward[0].toDouble(), forward[2].toDouble())
            )).toFloat()
            for (i in 0 until sampleN) {
                val at = indices[i]
                val u = mapped[i * 2]
                val v = mapped[i * 2 + 1]
                if (!u.isFinite() || !v.isFinite() ||
                    u < 0f || v < 0f ||
                    u >= imageDims[0].toFloat() ||
                    v >= imageDims[1].toFloat()) {
                    projectionRayAudit.invalidMapping(source)
                    continue
                }
                val z = zs[at]
                val texCam = PrecisionProjectionRayAudit.cameraRay(
                    xs[at].toFloat(), ys[at].toFloat(), z, fx, fy, cx, cy
                ) ?: continue
                val imageCam = PrecisionProjectionRayAudit.cameraRay(
                    u, v, z,
                    imageFocal[0], imageFocal[1],
                    imagePrincipal[0], imagePrincipal[1]
                ) ?: continue
                val texWorld = camera.pose.transformPoint(texCam)
                val imageWorld = camera.pose.transformPoint(imageCam)
                projectionRayAudit.record(source,
                    PrecisionProjectionRayAudit.Probe(
                        verticalDeltaCm = (texWorld[1] - imageWorld[1]) * 100f,
                        horizontalDeltaCm = kotlin.math.hypot(
                            texWorld[0] - imageWorld[0],
                            texWorld[2] - imageWorld[2]
                        ) * 100f,
                        depthM = z,
                        cameraPitchDeg = pitchDeg
                    )
                )
            }
        } catch (_: Exception) {
            // A geometry diagnostic must never fail the production scan.
            projectionRayAudit.error()
        }
    }

'''
c=one(c,
'''    private fun integrateImage(
        frame: Frame,''',
helper+'''    private fun integrateImage(
        frame: Frame,''',
"projection probe method")
c=one(c,
'''        if (count == 0) return false

        val levelFrame = GravityAlignedFrame.fromPose(referencePose)''',
'''        if (count == 0) return false

        // Diagnostic only: both candidate projection paths on SAME frame.
        // The original Raw/Full reconstruction code below is untouched.
        observeProjectionRayAudit(
            frame, depth, xs, ys, zs, count, fx, fy, cx, cy, isRaw
        )

        val levelFrame = GravityAlignedFrame.fromPose(referencePose)''',
"bounded per-frame projection probes")
if m.count("Precision 10.3")<2: raise RuntimeError("Expected v10.3 app label")
m=m.replace("Precision 10.3","Precision 10.4")
g=one(g,'versionName = "10.3"','versionName = "10.4"',"versionName")
g=one(g,'versionCode = 1030','versionCode = 1040',"versionCode")

audit=(root/"precision/PrecisionProjectionRayAudit.kt")
if not audit.exists() or 'fun cameraRay(' not in audit.read_text():
    raise RuntimeError("Missing testable projection model audit")
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m

collector.write_text(c,encoding="utf8")
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v10.4: independent projection-rig comparison per frame, diagnostic only")
