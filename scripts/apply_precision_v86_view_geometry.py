"""v8.6: capture camera-view geometry without changing numerical slope fits.

The saved point cloud is ball-relative, but the v8.5 camera quaternion was
world-relative. Store forward and right unit axes transformed to the SAME
gravity-aligned ball frame so offline view-angle comparisons are possible.
Also persist the effective camera intrinsics/basis used for Raw vs Full.
No added points, filtering, thresholds or camera acquisition passes.
"""
from pathlib import Path

root = Path("app/src/main/java/jp/example/greenreader")
collector = root / "precision/PrecisionDepthCollector.kt"
main = root / "MainActivity.kt"
gradle = Path("app/build.gradle.kts")
c = collector.read_text(encoding="utf8")
s = main.read_text(encoding="utf8")
g = gradle.read_text(encoding="utf8")

def one(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"v8.6 {label}: expected exactly once, got {n}")
    return src.replace(old, new, 1)

c = one(c,
'''            val cameraLocal = levelFrame.worldToLocal(camera.pose.translation)
            val q = camera.pose.rotationQuaternion
            framePoseTelemetry.record(''',
'''            val cameraLocal = levelFrame.worldToLocal(camera.pose.translation)
            // One transformed point for each axis is sufficient; both are
            // relative to cameraLocal in the same anchored local coordinate
            // system as the exported point cloud.
            val cameraForwardLocal = levelFrame.worldToLocal(
                camera.pose.transformPoint(floatArrayOf(0f, 0f, -1f))
            )
            val cameraRightLocal = levelFrame.worldToLocal(
                camera.pose.transformPoint(floatArrayOf(1f, 0f, 0f))
            )
            val projectionIntr = if (isRaw) null else camera.imageIntrinsics
            val imageBasis = if (isRaw) "raw_texture_scaled" else "cpu_image_pixels"
            val basisWidth = if (isRaw) depth.width else projectionIntr!!.imageDimensions[0]
            val basisHeight = if (isRaw) depth.height else projectionIntr!!.imageDimensions[1]
            val basisFx = if (isRaw) fx else projectionIntr!!.focalLength[0]
            val basisFy = if (isRaw) fy else projectionIntr!!.focalLength[1]
            val basisCx = if (isRaw) cx else projectionIntr!!.principalPoint[0]
            val basisCy = if (isRaw) cy else projectionIntr!!.principalPoint[1]
            val q = camera.pose.rotationQuaternion
            framePoseTelemetry.record(''',
"local pose and projection basis")
c = one(c,
'''                    qx = q[0], qy = q[1], qz = q[2], qw = q[3]
                )''',
'''                    qx = q[0], qy = q[1], qz = q[2], qw = q[3],
                    forwardLocalX = cameraForwardLocal[0] - cameraLocal[0],
                    forwardLocalY = cameraForwardLocal[1] - cameraLocal[1],
                    forwardLocalZ = cameraForwardLocal[2] - cameraLocal[2],
                    rightLocalX = cameraRightLocal[0] - cameraLocal[0],
                    rightLocalY = cameraRightLocal[1] - cameraLocal[1],
                    rightLocalZ = cameraRightLocal[2] - cameraLocal[2],
                    projectionBasis = imageBasis,
                    projectionWidth = basisWidth,
                    projectionHeight = basisHeight,
                    focalX = basisFx, focalY = basisFy,
                    principalX = basisCx, principalY = basisCy
                )''',
"pose camera basis fields")
if s.count('appVersion = "Precision 8.5"') < 2:
    raise SystemExit("v8.6 requires generated v8.5 meta and UI labels")
s = s.replace("Precision 8.5", "Precision 8.6")
g = one(g, 'versionName = "8.5"', 'versionName = "8.6"', "version name")
g = one(g, 'versionCode = 850', 'versionCode = 860', "version code")
assert "PrecisionScaleDirectionAudit.evaluate(" in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert "PrecisionDepthSourceAudit.analyze(" in s
assert "precisionFramePoseScanSummary()" in s
assert 'button("結果入力")' in s and 'button("次のホール")' in s
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
collector.write_text(c, encoding="utf8")
main.write_text(s, encoding="utf8")
gradle.write_text(g, encoding="utf8")
print("Applied v8.6 camera-ray geometry and projection basis telemetry")
