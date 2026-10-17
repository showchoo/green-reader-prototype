"""v11.2 static invariants: live image preview only, no released slope estimate."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
root=ROOT/"app/src/main/java/jp/example/greenreader"
capture=(root/"Camera2DepthCaptureActivity.kt").read_text(encoding="utf-8")
main=(root/"MainActivity.kt").read_text(encoding="utf-8")
archive=(root/"field/Camera2DepthArchive.kt").read_text(encoding="utf-8")
gradle=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")
assert "versionCode = 1120" in gradle
assert 'versionName = "11.2-depth16-live-preview"' in gradle
assert "Precision 11.2 DEPTH16プレビュー研究" in main
for marker in (
    "ImageFormat.DEPTH16","Color.rgb(229,30,130)",
    "Color.rgb(32,236,202)","depthPreview.setImageBitmap(bitmap)",
    "previewConfigured=true","captureReady=true",
    "if(!captureReady || frameCount>=MAX_FRAMES)return",
    "worker.postDelayed({","},1200L)",
    "registerResearchSensors()","sensorEvidence.add(",
    "sensorEvidence.csv()","sensorManager?.unregisterListener(listener)",
    "requestFinish(\"watchdog_timeout\")",
    "requestFinish(\"max_frames\")",
    "Camera2DepthArchive.save(","gravityCsv,summary,sensorCsv,sensorMetadata",
    "ByteOrder.nativeOrder()","PrecisionDepth16Codec.copyPacked("
):
    assert marker in capture,marker
assert capture.count("openCamera()")==2  # onCreate scheduled launch + definition
assert "worker.post {openCamera()}" not in capture
assert capture.index("if(!captureReady || frameCount>=MAX_FRAMES)return") < capture.index("val stats=PrecisionDepth16Codec.summary")
for marker in ("\"camera2_gravity.csv\"","\"camera2_sensor_events.csv\"",
               "\"camera2_sensor_metadata.json\"","\"record_identity.json\"",
               "DriveBackupScheduler.onScanSaved(context)"):
    assert marker in archive,marker
assert "PrecisionSlopeAnalyzer.analyze(" in main
assert "PrecisionRgbBurstRecorder.capture(" in main
print("v11.2: read-only camera preview before opt-in bounded DEPTH16/IMU capture, no production math changes")
