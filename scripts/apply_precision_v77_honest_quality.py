"""Green Reader v7.7: don't confuse repeatability with true slope accuracy.

Marker/referenced-distance concerns reduce confidence; Raw/Full frame
contributions stay visible. This patch does not distort or rescale slopes.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
quality=root/"precision/PrecisionQualityEstimator.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
q=quality.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit("v7.7 "+label+": expected 1 match, got "+str(n))
    return src.replace(old,new,1)

q=one(q,
'''        temporalCheckVerified: Boolean
    ): PrecisionScanQuality {''',
'''        temporalCheckVerified: Boolean,
        markerGeometryTrusted: Boolean = true
    ): PrecisionScanQuality {''',
"marker trust evaluator input")
q=one(q,
'''        val score = PrecisionTemporalQualityGate.score(rawScore, temporalCheckVerified)''',
'''        val score = PrecisionTemporalQualityGate.score(
            rawScore, temporalCheckVerified && markerGeometryTrusted
        )''',
"trust-aware quality cap")
q=one(q,
'''            temporalCheckVerified && score >= 85 && windowReports.size >= 2 &&''',
'''            temporalCheckVerified && markerGeometryTrusted &&
                score >= 85 && windowReports.size >= 2 &&''',
"trust-aware high confidence")

s=one(s,
'''                temporalCheckVerified = temporalResult.verified && !temporalResult.unstable
            )''',
'''                temporalCheckVerified = temporalResult.verified && !temporalResult.unstable,
                markerGeometryTrusted = precisionMarkerGeometry()?.needsReview != true
            )''',
"marker trust supplied to quality")
s=one(s,
'''-> "高精度"''',
'''-> "再現性良好"''',
"honest quality label")
s=s.replace("測定信頼度", "取得データ品質")
if "取得データ品質" not in s:raise SystemExit("Data quality label missing after change")
s=one(s,
'''                "\n推定ばらつき ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%（参考値）"''',
'''                "\n推定ばらつき ±" + String.format("%.2f", q.estimatedSlopeUncertaintyPercent) + "%（参考値）" +
                "\nDepth Raw=" + q.rawAcceptedFrames + " Full=" + q.fullAcceptedFrames +
                " / 絶対精度は未検証"''',
"show depth source mix and uncertainty disclosure")

assert 'button("次のホール")' in s
assert 'button("カップ再指定")' in s
assert 'button("実測距離")' in s
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()

if "Precision 7.6" not in s:raise SystemExit("v7.6 must precede v7.7")
s=s.replace("Precision 7.6","Precision 7.7")
g=one(g,'versionName = "7.6"','versionName = "7.7"',"Gradle version name")
g=one(g,'versionCode = 760','versionCode = 770',"Gradle version code")
main.write_text(s,encoding="utf8")
quality.write_text(q,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied Precision v7.7 marker-trust confidence and honest quality display")
