from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")

replacements = [
    (
        'status.text = "測定結果が揃いませんでした。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"',
        'status.text = "測定結果が揃いませんでした。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"'
    ),
    (
        'if (updateStatus) status.text = "測定結果が安定しませんでした。もう一度スキャンしてください"',
        'if (updateStatus) status.text = "測定結果が安定しませんでした。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"'
    ),
    (
        'if (updateStatus) status.text = "データ不足です。もう一度3秒スキャンしてください"',
        'if (updateStatus) status.text = "データ不足です。 " + precisionLastDiagnostic + " / もう一度スキャンしてください"'
    ),
]

changed = 0
for old, new in replacements:
    if old in s and old != new:
        s = s.replace(old, new)
        changed += 1

# Also make the diagnostic visible between windows whenever it already exists,
# so a later status overwrite cannot hide all evidence.
scan_status = 'if (scanning) status.text = "複数回測定中… 端末をゆっくり動かしてください"'
if scan_status in s:
    s = s.replace(
        scan_status,
        'if (scanning) status.text = "複数回測定中… " + precisionLastDiagnostic',
        1
    )
    changed += 1

if changed == 0:
    raise SystemExit("v1.8 diagnostic status targets not found")

s = s.replace('appVersion = "Precision 1.7"', 'appVersion = "Precision 1.8"')
main.write_text(s, encoding="utf-8")

build = Path("app/build.gradle.kts")
b = build.read_text(encoding="utf-8")
b = b.replace('versionCode = 170', 'versionCode = 180')
b = b.replace('versionName = "1.7"', 'versionName = "1.8"')
build.write_text(b, encoding="utf-8")

print(f"Applied Precision v1.8 persistent diagnostics ({changed} status paths)")
