from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")
s = s.replace('appVersion = "Precision 1.9"', 'appVersion = "Precision 2.0"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 190', 'versionCode = 200')
b = b.replace('versionName = "1.9"', 'versionName = "2.0"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v2.0 fixed-signing/OAuth diagnostics version bump")
