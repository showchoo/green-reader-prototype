"""Strict static invariants for v11.1 IMU evidence recording only."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
root=ROOT/"app/src/main/java/jp/example/greenreader"
main=(root/"MainActivity.kt").read_text(encoding="utf-8")
capture=(root/"Camera2DepthCaptureActivity.kt").read_text(encoding="utf-8")
archive=(root/"field/Camera2DepthArchive.kt").read_text(encoding="utf-8")
sensor=(root/"precision/Camera2SensorEvidence.kt").read_text(encoding="utf-8")
manifest=(ROOT/"app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
gradle=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")
assert 'versionCode = 1110' in gradle
assert 'versionName = "11.1-depth16-imu-evidence"' in gradle
assert 'Precision 11.1 Camera2 IMU研究' in main
assert 'Camera2DepthCaptureActivity::class.java' in main
assert 'android:name=".Camera2DepthCaptureActivity"' in manifest
assert 'ImageFormat.DEPTH16' in capture
assert 'CameraDevice.TEMPLATE_PREVIEW' in capture
assert 'ByteOrder.nativeOrder()' in capture
assert 'PrecisionDepth16Codec.copyPacked(' in capture
assert 'val raw=PrecisionDepth16Codec.copyPacked(' in capture
assert 'frameCount>=MAX_FRAMES' in capture
assert 'requestFinish("max_frames")' in capture
assert 'requestFinish("watchdog_timeout")' in capture
assert 'sensorManager?.unregisterListener(listener)' in capture
for code in (
    'Sensor.TYPE_GRAVITY', 'Sensor.TYPE_ACCELEROMETER',
    'Sensor.TYPE_GYROSCOPE', 'Sensor.TYPE_GYROSCOPE_UNCALIBRATED',
    'registerResearchSensors()', 'cameraTimestampSource',
    'SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME',
    'sensorEvidence.add(', 'sensorEvidence.csv()',
    'callback_elapsed_ns', 'gravityCsv,summary,sensorCsv,sensorMetadata'
):
    assert code in capture,code
for code in ('sensor_timestamp_ns','callback_elapsed_ns','bias_x',
             'bias_y','bias_z','perTypeLimit','outOfOrder','dropped'):
    assert code in sensor,code
for code in ('"camera2_gravity.csv"','"camera2_depth_frames.csv"',
             '"camera2_sensor_events.csv"','"camera2_sensor_metadata.json"',
             'DriveBackupScheduler.onScanSaved(context)'):
    assert code in archive,code
assert archive.index('"camera2_sensor_metadata.json"') < archive.index('"record_identity.json"')
assert 'metric_slope_certified' in archive
assert 'PrecisionSlopeAnalyzer.analyze(' in main
assert 'PrecisionDepthSourceAudit.analyze(' in main
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in main
assert 'PrecisionRgbBurstRecorder.capture(' in main
assert (ROOT/"app/src/test/java/jp/example/greenreader/precision/Camera2SensorEvidenceTest.kt").exists()
print("v11.1: bounded raw IMU, preserved DEPTH16 format and legacy gravity CSV, no putting accuracy claim")
