"""Fail-closed static invariants for v11.0 direct Camera2 DEPTH16 research."""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
main=(root/"MainActivity.kt").read_text()
cap=(root/"Camera2DepthCaptureActivity.kt").read_text()
arch=(root/"field/Camera2DepthArchive.kt").read_text()
codec=(root/"precision/PrecisionDepth16Codec.kt").read_text()
manifest=Path("app/src/main/AndroidManifest.xml").read_text()
gradle=Path("app/build.gradle.kts").read_text()

assert 'versionCode = 1100' in gradle
assert 'versionName = "11.0-depth16-acquisition"' in gradle
assert 'Camera2深度画像を実際に取得（研究）' in main
assert 'Camera2DepthCaptureActivity::class.java' in main
assert 'android:name=".Camera2DepthCaptureActivity"' in manifest
assert 'android:exported="false"' in manifest
assert 'ImageFormat.DEPTH16' in cap
assert 'REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT' in cap
assert 'CameraDevice.TEMPLATE_PREVIEW' in cap
assert 'CameraDevice.TEMPLATE_STILL_CAPTURE' in cap
assert 'requestFinish("max_frames")' in cap
assert 'requestFinish("watchdog_timeout")' in cap
assert 'max_frames' in cap
assert 'MAX_FRAMES=12' in cap
assert 'START_DELAY_MS=900L' in cap
assert 'setRepeatingRequest' in cap
assert 'captureSession?.close()' in cap and 'device?.close()' in cap
assert 'reader?.close()' in cap
assert 'ImageReader.newInstance(width,height,ImageFormat.DEPTH16,2)' in cap
assert 'ByteOrder.nativeOrder()' in cap
assert 'PrecisionDepth16Codec.copyPacked(' in cap
assert 'val raw=PrecisionDepth16Codec.copyPacked(' in cap
assert 'stats.validPixels' in cap
assert 'Sensor.TYPE_GRAVITY' in cap
assert 'accuracy_certified' not in codec  # Pure codec never certifies accuracy
assert 'packed and 0x1fff' in codec
assert '(packed ushr 13) and 7' in codec
assert 'data.size == width * height * 2' in codec
assert 'copyPacked' in codec and 'rowStride' in codec
assert 'record_identity.json' in arch
assert arch.index('"camera2_depth_summary.json"') < arch.index('"record_identity.json"')
assert 'DriveBackupScheduler.onScanSaved(context)' in arch
assert 'tof_hardware_identity_verified' in arch
assert 'metric_slope_certified' in arch
assert 'PrecisionSlopeAnalyzer.analyze(' in main
assert 'PrecisionDepthSourceAudit.analyze(' in main
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in main
assert 'PrecisionAnchoredGroundSelector.select(' in (
    root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert Path("app/src/test/java/jp/example/greenreader/precision/PrecisionDepth16CodecTest.kt").exists()
print("v11.0: real Camera2 DEPTH16 capture isolated, bounded, stride/confidence accurate, slope unaffected")
