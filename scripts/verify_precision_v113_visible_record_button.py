"""v11.3 generated source checks for visible record control and compatible capture."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"app/src/main/java/jp/example/greenreader/Camera2DepthCaptureActivity.kt"
s=p.read_text(encoding="utf-8")
g=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")
main=(ROOT/"app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")
archive=(ROOT/"app/src/main/java/jp/example/greenreader/field/Camera2DepthArchive.kt").read_text(encoding="utf-8")
assert "versionCode = 1130" in g
assert 'versionName = "11.3-depth16-visible-record-button"' in g
assert "Precision 11.3 深度プレビュー・記録" in main
assert 'text="記録開始（プレビュー確認後）"' in s
assert 'text="DEPTH16 記録画面 11.3（研究専用）"' in s
assert s.count("layout.addView(button,") == 1
assert s.count("layout.addView(depthPreview,") == 1
assert s.index("layout.addView(button,") < s.index("layout.addView(depthPreview,")
assert s.index("layout.addView(depthPreview,") < s.index("setContentView(layout)")
assert "LinearLayout.LayoutParams.MATCH_PARENT,0,1.0f" in s
assert "LinearLayout.LayoutParams.WRAP_CONTENT" in s
assert "textSize=18f" in s
assert "minHeight=64" in s
for token in (
    "ImageFormat.DEPTH16",
    "if(!previewConfigured) {",
    "previewConfigured=true",
    "captureReady=true",
    "if(!captureReady || frameCount>=MAX_FRAMES)return",
    'requestFinish("max_frames")',
    'requestFinish("watchdog_timeout")',
    "Camera2DepthArchive.save(",
    "gravityCsv,summary,sensorCsv,sensorMetadata",
    "sensorEvidence.csv()",
    "sensorManager?.unregisterListener(listener)",
    "depthPreview.setImageBitmap(bitmap)",
):
    assert token in s,token
for token in ('"camera2_depth_frames.csv"','"camera2_sensor_events.csv"',
              '"camera2_sensor_metadata.json"','"record_identity.json"',
              "DriveBackupScheduler.onScanSaved(context)"):
    assert token in archive,token
assert "PrecisionSlopeAnalyzer.analyze(" in main
assert "PrecisionRgbBurstRecorder.capture(" in main
print("v11.3: top record action visible independent of weighted preview; capture, backup, signer unchanged")
