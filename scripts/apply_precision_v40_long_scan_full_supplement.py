"""v6.0: version marker for long-scan Raw + Full Depth supplementation."""
from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")
if s.count('appVersion = "Precision 5.9"') != 1:
    raise SystemExit("v6.0 app version target missing")
s = s.replace('appVersion = "Precision 5.9"', 'appVersion = "Precision 6.0"', 1)
p.write_text(s, encoding="utf-8")

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "5.9"') != 1 or g.count('versionCode = 590') != 1:
    raise SystemExit("v6.0 Gradle version target missing")
g = g.replace('versionName = "5.9"', 'versionName = "6.0"', 1)
g = g.replace('versionCode = 590', 'versionCode = 600', 1)
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v6.0 long-scan Raw+Full Depth supplementation version")
