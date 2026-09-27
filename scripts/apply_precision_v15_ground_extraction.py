from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")
s = s.replace('appVersion = "Precision 1.4"', 'appVersion = "Precision 1.5"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 140', 'versionCode = 150')
b = b.replace('versionName = "1.4"', 'versionName = "1.5"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v1.5 ground extraction version bump")
