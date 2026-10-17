"""v11.3 UI hotfix: keep the research record button ABOVE the live preview.

The v11.2 generator attached the expanding preview before the sole button,
which risks pushing the button below the visible part of smaller screens.
No Camera2 pipeline, saved depth/IMU schema, or putting math changes.
"""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"scripts/build_precision_v112_depth_preview.py"],
               cwd=ROOT,check=True)

def replace_one(path,old,new):
    s=path.read_text(encoding="utf-8")
    if s.count(old)!=1:
        raise RuntimeError("Patch source invariant missing: "+old[:110])
    path.write_text(s.replace(old,new,1),encoding="utf-8")

gradle=ROOT/"app/build.gradle.kts"
replace_one(gradle,"versionCode = 1120","versionCode = 1130")
replace_one(gradle,'versionName = "11.2-depth16-live-preview"',
                   'versionName = "11.3-depth16-visible-record-button"')

main=ROOT/"app/src/main/java/jp/example/greenreader/MainActivity.kt"
s=main.read_text(encoding="utf-8")
if s.count("Precision 11.2 DEPTH16プレビュー研究")<2:
    raise RuntimeError("Missing v11.2 research entry")
main.write_text(s.replace("Precision 11.2 DEPTH16プレビュー研究",
                          "Precision 11.3 深度プレビュー・記録"),
                encoding="utf-8")

capture=ROOT/"app/src/main/java/jp/example/greenreader/Camera2DepthCaptureActivity.kt"
# Create the preview control before the button, but do not add it to the layout
# until AFTER the button. A weighted ImageView must be the final child.
preview_add="""        layout.addView(depthPreview,LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,0,1.0f))
"""
s=capture.read_text(encoding="utf-8")
if s.count(preview_add)!=1:
    raise RuntimeError("Cannot find preview layout insertion")
s=s.replace(preview_add,"",1)
old="        layout.addView(button)\n        setContentView(layout)"
new="""        // Fixed-size tap target before any weighted/expanding child.
        // The only record button stays at the top of the research screen.
        layout.addView(button,LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT))
        layout.addView(depthPreview,LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,0,1.0f))
        setContentView(layout)"""
if s.count(old)!=1:raise RuntimeError("Cannot locate research button in layout")
s=s.replace(old,new,1)
if s.count('text="深度画像を確認して記録開始"')!=1:
    raise RuntimeError("Record text missing")
s=s.replace('text="深度画像を確認して記録開始"',
            'text="記録開始（プレビュー確認後）"\n            textSize=18f\n            minHeight=64',1)
s=s.replace('text="Camera2 ライブ深度プレビュー（研究専用）"',
            'text="DEPTH16 記録画面 11.3（研究専用）"',1)
capture.write_text(s,encoding="utf-8")

subprocess.run([sys.executable,"scripts/verify_precision_v113_visible_record_button.py"],
               cwd=ROOT,check=True)
print("v11.3: record control above weighted preview, 1130, existing capture/backup unchanged")
