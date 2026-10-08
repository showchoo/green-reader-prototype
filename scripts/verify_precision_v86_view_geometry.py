"""v8.6 static preservation guards for diagnostic-only camera view geometry."""
from pathlib import Path
r=Path("app/src/main/java/jp/example/greenreader")
c=(r/"precision/PrecisionDepthCollector.kt").read_text(encoding="utf8")
t=(r/"precision/PrecisionFramePoseTelemetry.kt").read_text(encoding="utf8")
m=(r/"MainActivity.kt").read_text(encoding="utf8")
g=Path("app/build.gradle.kts").read_text(encoding="utf8")
rec=(r/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
assert 'versionName = "8.6"' in g and 'versionCode = 860' in g
assert 'appVersion = "Precision 8.6"' in m
assert 'cameraForwardLocal = levelFrame.worldToLocal(' in c
assert 'cameraRightLocal = levelFrame.worldToLocal(' in c
assert 'forwardLocalX = cameraForwardLocal[0] - cameraLocal[0]' in c
assert 'rightLocalZ = cameraRightLocal[2] - cameraLocal[2]' in c
assert 'projectionBasis = imageBasis' in c
assert 'if (isRaw) "raw_texture_scaled" else "cpu_image_pixels"' in c
assert 'projectionWidth = basisWidth' in c and 'focalX = basisFx' in c
assert 'framePoseTelemetry.record(' in c
assert 'depthTimestampNs = timestamp' in c
assert 'cameraFrameTimestampNs = frame.timestamp' in c
assert 'FRAME_POSE_V1_BEGIN' in t and 'FRAME_POSE_V1_END' in t
assert 'camera_forward_local_x' in t and 'intrinsics_fx' in t
assert 'PrecisionScaleDirectionAudit.evaluate(' in m
assert 'PrecisionPairedFlankAudit.evaluate(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'precisionFramePoseScanSummary()' in m
assert 'precision_depth_sources.csv' in rec
assert 'button("結果入力")' in m and 'button("次のホール")' in m
assert 'button("カップ再指定")' in m
assert 'bitmap = failureBitmap' in m
print("v8.6 source and prior field-feature regression checks passed")
