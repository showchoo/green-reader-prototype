"""Research v10.9 contract: read Camera2 metadata; don't open cameras/scan."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
m=(root/"MainActivity.kt").read_text()
r=(root/"field/ScanFieldRecorder.kt").read_text()
p=(root/"precision/PrecisionCamera2DepthProbe.kt").read_text()
gradle=Path("app/build.gradle.kts").read_text()
assert 'versionName = "10.9-camera2-probe"' in gradle
assert 'versionCode = 1090' in gradle
assert 'Precision 10.9 Camera2研究' in m
assert 'ToF / Camera2深度を確認・保存' in m
assert 'PrecisionCamera2DepthProbe.probe(this)' in m
assert 'ScanFieldRecorder.saveHardwareProbe(this,report.json)' in m
assert 'REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT' in p
assert 'ImageFormat.DEPTH16' in p
assert 'ImageFormat.DEPTH_POINT_CLOUD' in p
assert 'physicalCameraIds' in p
assert 'openCamera(' not in p
assert 'camera2_capabilities.json' in r
assert 'record_identity.json' in r
assert 'Putt_000/Scan_01_CAMERA2' in r
assert 'accuracy_certified' in p and 'false' in p
assert 'tof_physical_sensor_identity_verified' in p
assert 'DriveBackupScheduler.onScanSaved(context)' in r
assert r.index('fun saveHardwareProbe(') < r.index('private fun groupedFolder(')
assert r.index('writeDownload(context,rel,"camera2_capabilities.json"') < r.index('writeDownload(context,rel,"record_identity.json"')
assert 'PrecisionRgbBurstRecorder.capture(' in m
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionAnchoredGroundSelector.select(' in (
    root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert Path("app/src/test/java/jp/example/greenreader/precision/PrecisionCamera2DepthProbeTest.kt").exists()
print("v10.9: no-open read-only Camera2 DEPTH16 feature probe, drive marker final, existing slope gates intact")
