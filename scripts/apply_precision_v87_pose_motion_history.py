"""v8.7 diagnostic-only tracked frame history for Depth pose/latency audit.

The current-frame pose used by the existing point-cloud reconstruction is
NOT changed here. We only capture tracked camera frame poses and compare
against the Depth image acquisition timestamp in the saved diagnostics.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
collector=root/"precision/PrecisionDepthCollector.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
c=collector.read_text(encoding="utf8")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(src,old,new,label):
    n=src.count(old)
    if n!=1:raise SystemExit(f"v8.7 {label}: expected once got {n}")
    return src.replace(old,new,1)

c=one(c,
'''        lastRequestedMaxDepthM = maxDepthM
        attemptedFrames++

        var rawAccepted = false''',
'''        lastRequestedMaxDepthM = maxDepthM
        attemptedFrames++

        // Keep the recent tracked AR Frame poses independently of whether
        // Raw/Full Depth becomes available. Depth images can lag the Frame.
        // This is optional telemetry: failures must never interrupt scanning.
        try {
            val level = GravityAlignedFrame.fromPose(referencePose)
            val pose = camera.pose
            val xyz = level.worldToLocal(pose.translation)
            val forwardEnd = level.worldToLocal(
                pose.transformPoint(floatArrayOf(0f, 0f, -1f))
            )
            framePoseTelemetry.recordCameraFrame(
                PrecisionFramePoseTelemetry.CameraFramePose(
                    frameTimestampNs = frame.timestamp,
                    x = xyz[0], y = xyz[1], z = xyz[2],
                    forwardX = forwardEnd[0] - xyz[0],
                    forwardY = forwardEnd[1] - xyz[1],
                    forwardZ = forwardEnd[2] - xyz[2]
                )
            )
        } catch (_: Throwable) {
            // Observational diagnostic only. Never block a valid scan.
        }

        var rawAccepted = false''',
"tracked frame history before depth acquisition")
assert 'framePoseTelemetry.record(' in c
assert 'framePoseTelemetry.clear()' in c
assert 'depthTimestampNs = timestamp' in c
assert 'cameraFrameTimestampNs = frame.timestamp' in c

if s.count('appVersion = "Precision 8.6"')<2:
    raise SystemExit("v8.7 generated v8.6 app version labels missing")
s=s.replace("Precision 8.6", "Precision 8.7")
g=one(g,'versionName = "8.6"','versionName = "8.7"',"versionName")
g=one(g,'versionCode = 860','versionCode = 870',"versionCode")
assert "PrecisionScaleDirectionAudit.evaluate(" in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert "PrecisionDepthSourceAudit.analyze(" in s
assert "precisionFramePoseScanSummary()" in s
assert 'button("次のホール")' in s
assert 'button("結果入力")' in s
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
collector.write_text(c,encoding="utf8")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied Precision v8.7 historical frame pose + Depth latency diagnostic")
