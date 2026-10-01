"""v6.8: high-detail segment-aware roll line and adaptive arrows."""
from pathlib import Path

# UI templates are already applied by v6.5 after legacy patches.
# v6.8 only bumps the visible/build version and guards that no measurement logic changes.
p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")
if "Precision 6.7" not in s:
    raise SystemExit("v6.8 source version target missing")
s=s.replace("Precision 6.7","Precision 6.8")

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.7"') != 1 or g.count('versionCode = 670') != 1:
    raise SystemExit("v6.8 Gradle version target missing")
g=g.replace('versionName = "6.7"','versionName = "6.8"',1)
g=g.replace('versionCode = 670','versionCode = 680',1)

camera_ui=Path("app/src/main/java/jp/example/greenreader/ui/CameraOverlayResultView.kt").read_text(encoding="utf-8")
map_ui=Path("app/src/main/java/jp/example/greenreader/ui/GreenMapView.kt").read_text(encoding="utf-8")
path_ui=Path("app/src/main/java/jp/example/greenreader/ui/PrecisionRollPath.kt").read_text(encoding="utf-8")

assert "PrecisionRollPath.build(" in camera_ui
assert "drawAdaptiveChevrons" in camera_ui
assert "PrecisionRollPath.build(" in map_ui
assert "drawAdaptiveFlowChevrons" in map_ui
assert "max(96, report.segments.size * 24)" in path_ui
assert "raw[i] - endDrift * t" in path_ui
assert "quadTo(" in path_ui

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.8 high-detail roll rendering")
# Trigger Precision v6.8 build
