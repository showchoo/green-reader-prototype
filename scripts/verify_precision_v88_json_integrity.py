"""v8.8 post-generation check: valid JSON templates and saved field features.

This catches the old v7.1 bug: Kotlin triple-quoted JSON raw strings must
contain literal '"' keys, not '\\"' key delimiters. A synthetic substitution
checks the four generated JSON template payloads with Python json.loads.
"""
import json
from pathlib import Path
import re

root=Path("app/src/main/java/jp/example/greenreader")
rec=(root/"field/ScanFieldRecorder.kt").read_text(encoding="utf8")
main=(root/"MainActivity.kt").read_text(encoding="utf8")
gradle=Path("app/build.gradle.kts").read_text(encoding="utf8")

def json_template(name):
    at=rec.index("private fun "+name+"(")
    start=rec.index('return """{',at)
    end=rec.index('"""',start+len('return """'))
    template=rec[start+len('return """'):end]
    if r'\"schema_version\"' in template:
        raise AssertionError(name+" raw JSON quotes are incorrectly escaped")
    template=re.sub(r'\$\{[^{}]*\}',"0",template)
    template=re.sub(r'\$[a-zA-Z_][a-zA-Z_0-9]*',"0",template)
    return json.loads(template)

for name in ("metadataJson", "failureMetadataJson", "recordIdentityJson", "qualityJson"):
    obj=json_template(name)
    assert isinstance(obj,dict),name
    if name=="qualityJson":
        assert "score" in obj
    else:
        assert "schema_version" in obj,name

esc_at=rec.index("private fun escape(s: String)")
esc=rec[esc_at:rec.index("\n    }",esc_at)+6]
for literal in (r"'\b' ->",r"'\u000c' ->",r"'\r' ->",
                r"'\t' ->",r"ch.code < 0x20",r'append("\\u")'):
    assert literal in esc,("Missing control escape",literal)

assert 'versionName = "8.8"' in gradle
assert 'versionCode = 880' in gradle
assert 'appVersion = "Precision 8.8"' in main
assert "PrecisionScaleDirectionAudit.evaluate(" in main
assert "PrecisionPairedFlankAudit.evaluate(" in main
assert "PrecisionDepthSourceAudit.analyze(" in main
assert 'framePoseTelemetry.recordCameraFrame(' in (root/"precision/PrecisionDepthCollector.kt").read_text()
assert 'precision_depth_sources.csv' in rec
assert 'bitmap = failureBitmap' in main
assert 'button("次のパット")' in main and 'button("結果入力")' in main
assert 'button("次のホール")' in main
assert 'precisionFramePoseScanSummary()' in main
print("v8.8 all four generated JSON templates parse, escapes safe, prior workflows intact")
