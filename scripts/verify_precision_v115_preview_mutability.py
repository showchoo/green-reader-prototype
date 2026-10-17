"""v11.5 CI regression against accidental immutable preview Bitmap.

Static source verification matters here: v11.4 passed Android compilation but the
Bitmap created from colors[] cannot be drawn into via Canvas on a real device.
Android's Bitmap(width,height,Config) is mutable by contract.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
root=ROOT/"app/src/main/java/jp/example/greenreader"
preview=(root/"Camera2DepthCaptureActivity.kt").read_text(encoding="utf-8")
gradle=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")
main=(root/"MainActivity.kt").read_text(encoding="utf-8")
archive=(root/"field/Camera2DepthArchive.kt").read_text(encoding="utf-8")

assert "versionCode = 1150" in gradle
assert 'versionName = "11.5-depth16-mutable-preview-fix"' in gradle
assert main.count("Precision 11.5 深度プレビュー修正版")>=2
assert 'text="DEPTH16 記録画面 11.5（研究専用）"' in preview
for marker in (
    "val bitmap=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888)",
    "bitmap.setPixels(colors,0,width,0,0,width,height)",
    'check(bitmap.isMutable)',
    "val canvas=Canvas(bitmap)",
    "catch(e:RuntimeException)",
    "Optional guide overlay failed; showing raw depth preview",
    'canvas.drawRect(x0,y0,x1,y1,guide)',
    "depthPreview.setImageBitmap(bitmap)",
    'text="記録開始（プレビュー確認後）"',
    "sensorEvidence.csv()",
    "Camera2DepthArchive.save(",
    'requestFinish("max_frames")',
    'requestFinish("watchdog_timeout")',
):
    assert marker in preview, marker
assert "Bitmap.createBitmap(colors,width,height,Bitmap.Config.ARGB_8888)" not in preview
assert not re.search(r"Bitmap.createBitmap\(\s*colors\s*,", preview)
assert preview.index("bitmap.setPixels(")<preview.index("check(bitmap.isMutable)")<preview.index("val canvas=Canvas(bitmap)")
assert preview.index("catch(e:RuntimeException)") < preview.index("depthPreview.setImageBitmap(bitmap)")
assert preview.index("layout.addView(button,")<preview.index("layout.addView(depthPreview,")
assert "if(!captureReady || frameCount>=MAX_FRAMES)return" in preview
assert "registerResearchSensors()" in preview
assert "ByteOrder.nativeOrder()" in preview
assert "PrecisionDepth16Codec.copyPacked(" in preview
assert ".put(\"app_version\",buildVersion)" in archive
assert "record_identity.json" in archive
assert "DriveBackupScheduler.onScanSaved(context)" in archive
assert "PrecisionSlopeAnalyzer.analyze(" in main
assert "PrecisionRgbBurstRecorder.capture(" in main
print("v11.5: mutable pixel storage before optional Canvas overlay; recording and archive unaffected")
