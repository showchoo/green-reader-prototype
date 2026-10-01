"""v6.6: stabilize AR startup and lighten the live HUD without changing result animations."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.6 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

# ARCore needs a healthy cadence while initial tracking is converging.
once(
'''            val precisionActive = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (precisionActive) 33L else 250L)
''',
'''            val arInitializing = trackingStateText != TrackingState.TRACKING.name
            val precisionActive = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (arInitializing || precisionActive) 33L else 250L)
''',
"startup render cadence"
)

# Once AR starts tracking, replace the stale startup text even if the user
# has not started a scan yet.
once(
'''            latestFrame = f
            trackingStateText = f.camera.trackingState.name
            val latestPose = f.camera.displayOrientedPose
''',
'''            latestFrame = f
            val previousTracking = trackingStateText
            trackingStateText = f.camera.trackingState.name
            if (previousTracking != TrackingState.TRACKING.name &&
                trackingStateText == TrackingState.TRACKING.name &&
                !scanning && pendingMark == null && markMode == 0
            ) {
                runOnUiThread {
                    if (status.text.toString().startsWith("AR準備中")) {
                        status.text = "AR準備完了。ボール位置から設定してください"
                    }
                }
            }
            val latestPose = f.camera.displayOrientedPose
''',
"startup status handoff"
)

s=s.replace('Precision 6.5','Precision 6.6')

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.5"') != 1 or g.count('versionCode = 650') != 1:
    raise SystemExit("v6.6 gradle version target missing")
g=g.replace('versionName = "6.5"','versionName = "6.6"',1)
g=g.replace('versionCode = 650','versionCode = 660',1)

assert "val arInitializing = trackingStateText != TrackingState.TRACKING.name" in s
assert 'status.text = "AR準備完了。ボール位置から設定してください"' in s

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.6 AR startup stabilization")
# Trigger Precision v6.6 build
