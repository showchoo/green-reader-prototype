from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

old = 'status.text = "測定結果が揃いませんでした。もう一度スキャンしてください"'
new = 'status.text = "測定結果が揃いませんでした。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"'
if old not in s:
    raise SystemExit("v1.7 failure status target missing")
s = s.replace(old, new, 1)
s = s.replace('appVersion = "Precision 1.6"', 'appVersion = "Precision 1.7"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 160', 'versionCode = 170')
b = b.replace('versionName = "1.6"', 'versionName = "1.7"')
build.write_text(b, encoding="utf-8")

print("Applied Precision v1.7 relaxed gates and diagnostics")
