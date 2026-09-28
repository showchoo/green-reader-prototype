"""v6.3: stronger idle power saving without changing scan/Depth cadence."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.3 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

# Keep all precision-sensitive/interactive work at the existing ~30 fps.
# Only camera-idle rendering is reduced from ~7 fps (140 ms) to 4 fps (250 ms).
once(
'''            val fast = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (fast) 33L else 140L)
''',
'''            val precisionActive = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (precisionActive) 33L else 250L)
''',
"idle render cadence"
)

# Version bump only; no scan/Depth/analyzer thresholds are changed.
if s.count('appVersion = "Precision 6.2"') != 1:
    raise SystemExit("v6.3 app version target missing")
s=s.replace('appVersion = "Precision 6.2"','appVersion = "Precision 6.3"',1)

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.2"') != 1 or g.count('versionCode = 620') != 1:
    raise SystemExit("v6.3 gradle version target missing")
g=g.replace('versionName = "6.2"','versionName = "6.3"',1)
g=g.replace('versionCode = 620','versionCode = 630',1)

# Guard the safety boundary explicitly.
assert "if (precisionActive) 33L else 250L" in s
assert "precisionCollector.integrate(" in s
assert "pixelStrideStep = 4" in s

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.3 stronger idle power saving")
# Trigger Precision v6.3 build
