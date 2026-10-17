"""Generate v11.4 native depth-image aiming guides and trustworthy ZIP version.

Stacked on verified v11.3 generator. Does not change DEPTH16 numbers, saved
frame format, IMU timing, putt/grade algorithms or default research opt-in.
"""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"scripts/build_precision_v113_visible_record_button.py"],cwd=ROOT,check=True)

def patch(path, old, new):
    text=path.read_text(encoding="utf-8")
    if text.count(old)!=1:
        raise RuntimeError(f"Expected one source marker in {path}: {old[:100]}")
    path.write_text(text.replace(old,new,1),encoding="utf-8")

gradle=ROOT/"app/build.gradle.kts"
patch(gradle,"versionCode = 1130","versionCode = 1140")
patch(gradle,'versionName = "11.3-depth16-visible-record-button"',
             'versionName = "11.4-depth16-native-aiming-guides"')

main=ROOT/"app/src/main/java/jp/example/greenreader/MainActivity.kt"
v=main.read_text(encoding="utf-8")
old="Precision 11.3 深度プレビュー・記録"
if v.count(old)<2:raise RuntimeError("Missing v11.3 main activity entry")
main.write_text(v.replace(old,"Precision 11.4 深度位置ガイド"),encoding="utf-8")

activity=ROOT/"app/src/main/java/jp/example/greenreader/Camera2DepthCaptureActivity.kt"
patch(activity,"import android.graphics.Bitmap\n",
               "import android.graphics.Bitmap\nimport android.graphics.Canvas\nimport android.graphics.Paint\n")
patch(activity,
      'text="DEPTH16 記録画面 11.3（研究専用）"',
      'text="DEPTH16 記録画面 11.4（研究専用）"')
patch(activity,
      '"板とその周囲がすべて映っているのを確認してから記録してください。\\n"+',
      '"黄色の枠から板がはみ出さず、周囲も灰色で深度が取れる位置へ。\\n"+')
patch(activity,
      'val bitmap=Bitmap.createBitmap(colors,width,height,Bitmap.Config.ARGB_8888)',
      '''val bitmap=Bitmap.createBitmap(colors,width,height,Bitmap.Config.ARGB_8888)
        // Draw into preview bitmap ONLY. The archived raw DEPTH16 bytes,
        // vendor confidence and pixel coordinates are not changed.
        // ImageView FIT_CENTER preserves the original 640×480 pixel axes.
        val canvas=Canvas(bitmap)
        val guide=Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color=Color.rgb(255,205,55)
            strokeWidth=3f
            style=Paint.Style.STROKE
        }
        // A visual 15% horizontal / 18% vertical inset. This is not a
        // measured board region, camera calibration or valid-pixel mask.
        val x0=width*0.15f
        val y0=height*0.18f
        val x1=width*0.85f
        val y1=height*0.82f
        canvas.drawRect(x0,y0,x1,y1,guide)
        val labelBg=Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color=Color.argb(185,8,13,18)
            style=Paint.Style.FILL
        }
        canvas.drawRect(4f,3f,282f,36f,labelBg)
        val label=Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color=Color.WHITE
            textSize=21f
            style=Paint.Style.FILL
        }
        canvas.drawText("DEPTH x ->   y down",12f,27f,label)''')

# The legacy archive used a static string Precision 11.1 even for v11.2,
# v11.3. Save installed PackageInfo.versionName without overstating accuracy.
archive=ROOT/"app/src/main/java/jp/example/greenreader/field/Camera2DepthArchive.kt"
patch(archive,
      'val identity=JSONObject()',
      '''val buildVersion=try {
            context.packageManager.getPackageInfo(context.packageName,0)
                .versionName ?: "unknown"
        } catch (_:Exception) { "unknown" }
        val identity=JSONObject()''')
patch(archive,
      '.put("app_version","Precision 11.1 Camera2 IMU研究")',
      '.put("app_version",buildVersion)')

subprocess.run([sys.executable,"scripts/verify_precision_v114_native_guides.py"],cwd=ROOT,check=True)
print("v11.4: native-coordinate visual-only guide + correct archive app_version; capture math unchanged")
