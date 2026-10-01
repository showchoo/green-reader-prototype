"""v5.8: version marker for long-range cup pair gating."""
from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")
if s.count('appVersion = "Precision 5.7"') != 1:
    raise SystemExit("v5.8 app version target missing")
s = s.replace('appVersion = "Precision 5.7"', 'appVersion = "Precision 5.8"', 1)
p.write_text(s, encoding="utf-8")

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "5.7"') != 1 or g.count('versionCode = 570') != 1:
    raise SystemExit("v5.8 Gradle version target missing")
g = g.replace('versionName = "5.7"', 'versionName = "5.8"', 1)
g = g.replace('versionCode = 570', 'versionCode = 580', 1)
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v5.8 long-range cup pair-gate version")
# Trigger Precision v5.8 build
