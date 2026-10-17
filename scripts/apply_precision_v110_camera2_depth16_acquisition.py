"""Precision 11.0 research: open a separate Camera2 DEPTH16 Activity.

Intentionally keeps the ARCore scan and slope math exactly v10.9; the new
Activity starts only when the user presses an explicit MENU button.
Camera2 DEPTH_DEPTH_IS_EXCLUSIVE prohibits simultaneous RGB in one capture.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
manifest=Path("app/src/main/AndroidManifest.xml")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
x=manifest.read_text(encoding="utf8")

def once(s,old,new,name):
    n=s.count(old)
    if n!=1:raise RuntimeError(f"v11.0 {name}: expected 1 found {n}")
    return s.replace(old,new,1)

m=once(m,
'''        expandedMenu.addView(camera2Row)''',
'''        expandedMenu.addView(camera2Row)

        val depth16Row=LinearLayout(this).apply {
            orientation=LinearLayout.HORIZONTAL
        }
        depth16Row.addView(button("Camera2深度画像を実際に取得（研究）") {
            if (scanning) {
                Toast.makeText(this,
                    "現在のスキャンが終了してから深度カメラを起動してください",
                    Toast.LENGTH_LONG).show()
            } else {
                // Opening a separate Activity triggers MainActivity.onPause(),
                // releasing the ARCore camera before opening depth-only ID 4.
                startActivity(android.content.Intent(
                    this,Camera2DepthCaptureActivity::class.java))
            }
        },LinearLayout.LayoutParams(-1,dp(42)))
        expandedMenu.addView(depth16Row)''',
"new isolated research button")

x=once(x,
'''        <activity
            android:name=".DataManagerActivity"''',
'''        <activity
            android:name=".Camera2DepthCaptureActivity"
            android:screenOrientation="portrait"
            android:exported="false" />

        <activity
            android:name=".DataManagerActivity"''',
"activity declaration")

if m.count("Precision 10.9 Camera2研究")<2:
    raise RuntimeError("expected generated v10.9 version labels")
m=m.replace("Precision 10.9 Camera2研究","Precision 11.0 Camera2深度研究")
g=once(g,'versionName = "10.9-camera2-probe"',
       'versionName = "11.0-depth16-acquisition"',"versionName")
g=once(g,'versionCode = 1090','versionCode = 1100',"versionCode")
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionRgbBurstRecorder.capture(' in m
assert 'PrecisionCamera2DepthProbe.probe(this)' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/Camera2DepthArchive.kt").read_text()
assert 'PrecisionAnchoredGroundSelector.select(' in (
    root/"precision/PrecisionSurfaceBuilder.kt").read_text()
main.write_text(m,encoding="utf8")
manifest.write_text(x,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v11.0: independent Camera2 DEPTH16 capture activity, no ARCore slope changes")
