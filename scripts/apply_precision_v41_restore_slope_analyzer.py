"""v6.1: version marker after restoring canonical PrecisionSlopeAnalyzer."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")
if s.count('appVersion = "Precision 6.0"') != 1:
    raise SystemExit("v6.1 app version target missing")
s=s.replace('appVersion = "Precision 6.0"','appVersion = "Precision 6.1"',1)
p.write_text(s,encoding="utf-8")

gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.0"') != 1 or g.count('versionCode = 600') != 1:
    raise SystemExit("v6.1 Gradle version target missing")
g=g.replace('versionName = "6.0"','versionName = "6.1"',1)
g=g.replace('versionCode = 600','versionCode = 610',1)
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.1 canonical slope analyzer restore version")
