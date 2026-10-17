"""Offline static release invariants for research v11.4 generated sources."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"app/src/main/java/jp/example/greenreader"
activity=(p/"Camera2DepthCaptureActivity.kt").read_text(encoding="utf-8")
archive=(p/"field/Camera2DepthArchive.kt").read_text(encoding="utf-8")
main=(p/"MainActivity.kt").read_text(encoding="utf-8")
gradle=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")

assert "versionCode = 1140" in gradle
assert 'versionName = "11.4-depth16-native-aiming-guides"' in gradle
assert main.count("Precision 11.4 深度位置ガイド")>=2
assert 'text="DEPTH16 記録画面 11.4（研究専用）"' in activity
for marker in (
    "import android.graphics.Canvas",
    "import android.graphics.Paint",
    "val x0=width*0.15f",
    "val y0=height*0.18f",
    "val x1=width*0.85f",
    "val y1=height*0.82f",
    "canvas.drawRect(x0,y0,x1,y1,guide)",
    'canvas.drawText("DEPTH x ->   y down",12f,27f,label)',
    "深度が取れる位置",
    "ImageFormat.DEPTH16",
    "if(!captureReady || frameCount>=MAX_FRAMES)return",
    "registerResearchSensors()",
    "sensorEvidence.csv()",
    'requestFinish("max_frames")',
    'requestFinish("watchdog_timeout")',
    "depthPreview.setImageBitmap(bitmap)",
    "Camera2DepthArchive.save(",
):
    assert marker in activity,marker
assert activity.index("val bitmap=Bitmap.createBitmap") < activity.index("canvas.drawRect(x0") < activity.index("depthPreview.setImageBitmap(bitmap)")
assert activity.index("layout.addView(button,") < activity.index("layout.addView(depthPreview,")
assert archive.count("context.packageManager.getPackageInfo(context.packageName,0)")==1
assert '.put("app_version",buildVersion)' in archive
assert '"Precision 11.1 Camera2 IMU研究"' not in archive
for marker in ("record_identity.json","camera2_depth_frames.csv",
               "camera2_sensor_events.csv","camera2_sensor_metadata.json",
               "DriveBackupScheduler.onScanSaved(context)"):
    assert marker in archive,marker
assert archive.index('"camera2_sensor_metadata.json"') < archive.index('"record_identity.json"')
assert "PrecisionSlopeAnalyzer.analyze(" in main
print("v11.4: native-coordinate guides on preview only, true app_version in ZIP, legacy camera and putting preserved")
