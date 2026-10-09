"""v8.8: harden metadata JSON control-character escaping.

In Kotlin raw JSON templates, quotes must remain unescaped, while dynamic
user-supplied strings must be encoded as JSON strings. v7.3 fixed a prior
template quote bug; v8.8 extends dynamic-value escaping for ALL JSON ASCII
control characters to prevent invalid metadata from odd error text.
"""
from pathlib import Path
import re
root=Path("app/src/main/java/jp/example/greenreader")
rec=root/"field/ScanFieldRecorder.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
r=rec.read_text(encoding="utf8")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
anchor="    private fun escape(s: String)"
if r.count(anchor)!=1:
    raise SystemExit(f"v8.8 recorder escape count mismatch: {r.count(anchor)}")
start=r.index(anchor)
end=r.index("\n",start)
old=r[start:end]
if "replace(" not in old:
    raise SystemExit("v8.8 expected the old one-line JSON escape helper")
replacement=r'''    private fun escape(s: String): String = buildString(s.length + 16) {
        for (ch in s) {
            when (ch) {
                '\\' -> append("\\\\")
                '"' -> append("\\\"")
                '\b' -> append("\\b")
                '\u000c' -> append("\\f")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> {
                    if (ch.code < 0x20) {
                        append("\\u")
                        append(ch.code.toString(16).padStart(4, '0'))
                    } else {
                        append(ch)
                    }
                }
            }
        }
    }'''
r=r[:start]+replacement+r[end:]
if s.count("Precision 8.7") < 2:
    raise SystemExit("v8.8 generated v8.7 version labels missing")
s=s.replace("Precision 8.7","Precision 8.8")
if g.count('versionName = "8.7"')!=1 or g.count('versionCode = 870')!=1:
    raise SystemExit("v8.8 Gradle previous version fields missing")
g=g.replace('versionName = "8.7"','versionName = "8.8"')
g=g.replace('versionCode = 870','versionCode = 880')
# Earlier v7.3 patch must have fixed triple-quoted JSON keys.
for name in ("metadataJson", "failureMetadataJson"):
    pos=r.index("private fun "+name+"(")
    start=r.index('return """{',pos)
    end=r.index('"""',start+len('return """'))
    template=r[start:end]
    if r'\"schema_version\"' in template or r'\"app_version\"' in template:
        raise SystemExit(f"v8.8 {name} has legacy raw-JSON invalid quote escaping")
    if '"schema_version"' not in template:
        raise SystemExit(f"v8.8 {name} is missing schema JSON")
assert 'button("次のパット")' in s and 'button("結果入力")' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'PrecisionPairedFlankAudit.evaluate(' in s
assert 'PrecisionScaleDirectionAudit.evaluate(' in s
assert 'precision_depth_sources.csv' in r
rec.write_text(r,encoding="utf8")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied v8.8 JSON-control escaping and version 8.8, preserved diagnostics")
