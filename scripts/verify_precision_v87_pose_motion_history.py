"""v8.7 regression invariants: tracked frame history remains telemetry-only."""
from pathlib import Path

r = Path("app/src/main/java/jp/example/greenreader")
c = (r/"precision/PrecisionDepthCollector.kt").read_text(encoding="utf8")
t = (r/"precision/PrecisionFramePoseTelemetry.kt").read_text(encoding="utf8")
s = (r/"MainActivity.kt").read_text(encoding="utf8")
g = Path("app/build.gradle.kts").read_text(encoding="utf8")
rec = (r/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
offline = Path("scripts/analyze_precision_view_geometry.py").read_text(encoding="utf8")

assert 'versionName = "8.7"' in g and 'versionCode = 870' in g
assert 'appVersion = "Precision 8.7"' in s
assert 'framePoseTelemetry.recordCameraFrame(' in c
assert 'framePoseTelemetry.record(' in c
assert c.index('framePoseTelemetry.recordCameraFrame(') < c.index('frame.acquireRawDepthImage16Bits()')
assert 'frameTimestampNs = frame.timestamp' in c
assert 'cameraFrameCount(): Int' in t
assert 'nearestFrameFor(' in t
assert 'maxGapNs: Long = 80_000_000L' in t
assert 'if (gap > maxGapNs) return null' in t
assert 'camera_translation_delta_m' in t and 'camera_forward_delta_deg' in t
assert 'framePoseTelemetry.clear()' in c
assert "PrecisionScaleDirectionAudit.evaluate(" in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert "PrecisionDepthSourceAudit.analyze(" in s
assert 'precisionFramePoseScanSummary()' in s
assert 'precision_depth_sources.csv' in rec
assert 'bitmap = failureBitmap' in s
assert 'button("次のホール")' in s and 'button("結果入力")' in s
assert 'button("カップ再指定")' in s
assert 'pose_motion_status' in offline
assert 'view_comparison_status' in offline
print("v8.7 diagnostic frame history and prior field feature checks passed")
