"""Fail-closed integration invariants for opt-in RGB research capture."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
m=(root/"MainActivity.kt").read_text()
r=(root/"field/ScanFieldRecorder.kt").read_text()
c=(root/"field/PrecisionRgbBurstRecorder.kt").read_text()
codec=(root/"precision/PrecisionYuv420Nv21.kt").read_text()
archive=(root/"field/DriveBackupArchive.kt").read_text()
gradle=Path("app/build.gradle.kts").read_text()
assert 'versionName = "10.7-rgb-research"' in gradle
assert 'versionCode = 1070' in gradle
assert "Precision 10.7 RGB研究" in m
assert 'getBoolean("enabled",false)' in m
assert '研究記録を有効化' in m and '研究RGB連続記録: OFF' in m
assert 'PrecisionRgbBurstRecorder.begin(this,it)' in m
assert 'PrecisionRgbBurstRecorder.capture(' in m
assert m.index('PrecisionRgbBurstRecorder.capture(') < m.index(
    'collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)')
assert m.index('precisionCurrentRecord?.let {') < m.index('        scanning = true')
assert c.count('frame.acquireCameraImage().use') == 1
assert 'frame.camera.imageIntrinsics' in c
assert 'frame.camera.pose' in c and 'frame.androidSensorPose' in c
assert 'image.timestamp' in c and 'frame.timestamp' in c
assert 'sensor_timestamp_ns,callback_elapsed_ns' in c
assert 'MAX_IMAGES = 96' in c and 'MAX_PENDING_YUV = 3' in c
assert 'NotYetAvailableException' in c and 'permits.release()' in c
assert 'slope_certified' in c and 'false' in c
assert 'PrecisionYuv420Nv21.pack' in c and 'width*height*3/2' in codec
assert r.count('saveRgbResearchModern(context,folder,identity)') == 2
assert r.count('saveRgbResearchLegacy(dir,identity,context)') == 2
for chunk in r.split('saveRgbResearchModern(context,folder,identity)')[1:]:
    assert chunk.index('DriveBackupScheduler.onScanSaved(context)') < 300
for chunk in r.split('saveRgbResearchLegacy(dir,identity,context)')[1:]:
    assert chunk.index('DriveBackupScheduler.onScanSaved(context)') < 300
assert 'parts.size != 3' in archive
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'button("次のパット")' in m and 'button("結果入力")' in m
print("v10.7: opt-in raw CPU RGB, pose and inertial data archival with safe untouched slope + Drive backup hooks PASS")
