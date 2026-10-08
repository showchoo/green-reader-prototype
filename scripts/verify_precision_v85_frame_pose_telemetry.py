"""v8.5 generation regression: observation-only per-depth-frame camera poses."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
s=(root/"MainActivity.kt").read_text(encoding="utf8")
c=(root/"precision/PrecisionDepthCollector.kt").read_text(encoding="utf8")
t=(root/"precision/PrecisionFramePoseTelemetry.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
r=(root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
assert 'versionName = "8.5"' in g and 'versionCode = 850' in g
assert 'appVersion = "Precision 8.5"' in s
assert 'framePoseTelemetry.record(' in c
assert 'depthTimestampNs = timestamp' in c
assert 'cameraFrameTimestampNs = frame.timestamp' in c
assert 'framePoseTelemetry.clear()' in c
assert 'framePoseDiagnostics(): String' in c
assert s.count('precisionCollector.framePoseDiagnostics()') >= 2
assert 'FRAME_POSE_V1_BEGIN' in t and 'FRAME_POSE_V1_END' in t
assert 'droppedCount(): Int' in t
assert 'depth_timestamp_ns,camera_frame_timestamp_ns' in t
assert "PrecisionScaleDirectionAudit.evaluate(" in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert "PrecisionDepthSourceAudit.analyze(" in s
assert 'precision_depth_sources.csv' in r
assert 'button("次のホール")' in s and 'button("結果入力")' in s
assert 'button("カップ再指定")' in s
assert 'bitmap = failureBitmap' in s
print("v8.5 source telemetry, prior direction audits and auto-recording guards passed")
