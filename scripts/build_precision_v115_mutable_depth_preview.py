"""Repair v11.4 blank DEPTH16 preview caused by drawing on immutable Bitmap.

Android Bitmap.createBitmap(int[] colors,width,height,Config) produces an
IMMUTABLE bitmap. Canvas(bitmap) then throws IllegalStateException every time.
Create a mutable bitmap, copy pixel colors and draw native-coordinate guides
with error isolation so another overlay bug cannot break recording or preview.
"""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"scripts/build_precision_v114_native_guides.py"],
               check=True,cwd=ROOT)

def patch(path,old,new):
    s=path.read_text(encoding="utf-8")
    if s.count(old)!=1:
        raise RuntimeError("Expected exactly one marker in "+str(path)+": "+old[:110])
    path.write_text(s.replace(old,new,1),encoding="utf-8")

gradle=ROOT/"app/build.gradle.kts"
patch(gradle,"versionCode = 1140","versionCode = 1150")
patch(gradle,'versionName = "11.4-depth16-native-aiming-guides"',
             'versionName = "11.5-depth16-mutable-preview-fix"')

main=ROOT/"app/src/main/java/jp/example/greenreader/MainActivity.kt"
s=main.read_text(encoding="utf-8")
v="Precision 11.4 深度位置ガイド"
if s.count(v)<2:raise RuntimeError("MainActivity v11.4 link missing")
main.write_text(s.replace(v,"Precision 11.5 深度プレビュー修正版"),encoding="utf-8")

activity=ROOT/"app/src/main/java/jp/example/greenreader/Camera2DepthCaptureActivity.kt"
patch(activity,'text="DEPTH16 記録画面 11.4（研究専用）"',
               'text="DEPTH16 記録画面 11.5（研究専用）"')

# A Bitmap built directly from colors[] is immutable on Android, despite
# successful Kotlin/JVM compilation. Use explicitly mutable constructor.
patch(activity,
      'val bitmap=Bitmap.createBitmap(colors,width,height,Bitmap.Config.ARGB_8888)',
      '''val bitmap=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888)
        bitmap.setPixels(colors,0,width,0,0,width,height)
        check(bitmap.isMutable) { "Preview bitmap must be mutable for Canvas" }''')

# If the decoration itself fails for any reason, continue presenting the raw
# depth colors. Only preview decoration is downgraded; raw saved DEPTH16 is
# never changed. This prevents overlays from blanking the camera display.
patch(activity,
      '''        val canvas=Canvas(bitmap)
        val guide=Paint(Paint.ANTI_ALIAS_FLAG).apply {''',
      '''        try {
        val canvas=Canvas(bitmap)
        val guide=Paint(Paint.ANTI_ALIAS_FLAG).apply {''')
patch(activity,
      '''        canvas.drawText("DEPTH x ->   y down",12f,27f,label)
        ui.post {''',
      '''        canvas.drawText("DEPTH x ->   y down",12f,27f,label)
        } catch(e:RuntimeException) {
            // Keep presenting the decoded DEPTH16 even if a decorative
            // overlay fails. Never block the user's capture or saved frames.
            android.util.Log.w("GreenReaderDepthPreview",
                "Optional guide overlay failed; showing raw depth preview",e)
        }
        ui.post {''')

subprocess.run([sys.executable,"scripts/verify_precision_v115_preview_mutability.py"],
               check=True,cwd=ROOT)
print("v11.5: Android mutable bitmap + fail-open optional guide overlay; raw depth unchanged")
