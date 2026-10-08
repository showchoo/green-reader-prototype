"""Precision v7.5: gate high confidence on independently verified temporal stability."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
qpath=root/"precision/PrecisionQualityEstimator.kt"
mainpath=root/"MainActivity.kt"
gpath=Path("app/build.gradle.kts")
q=qpath.read_text(encoding="utf-8")
s=mainpath.read_text(encoding="utf-8")
g=gpath.read_text(encoding="utf-8")

def one(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit("v7.5 "+label+": expected 1, got "+str(n))
    return src.replace(old,new,1)

q=one(q,
'''        ball: Vec3,
        cup: Vec3
    ): PrecisionScanQuality {''',
'''        ball: Vec3,
        cup: Vec3,
        temporalCheckVerified: Boolean
    ): PrecisionScanQuality {''',
"evaluate param")
q=one(q,
'''        val score = (weighted * 100f).toInt().coerceIn(0, 100)''',
'''        val rawScore = (weighted * 100f).toInt().coerceIn(0, 100)
        // The temporal signal has not been calibrated against ground truth.
        // We only prevent an unverified scan from appearing highly certain.
        val score = PrecisionTemporalQualityGate.score(rawScore, temporalCheckVerified)''',
"score")
q=one(q,
'''            score >= 85 && windowReports.size >= 2 &&''',
'''            temporalCheckVerified && score >= 85 && windowReports.size >= 2 &&''',
"high precision eligibility")
q=one(q,
'''        val guidance = buildGuidance(
            surface = surface,''',
'''        val guidance = ((if (!temporalCheckVerified && report != null) {
            listOf("測定の時間的な一致を確認できませんでした。再スキャンで確認してください")
        } else emptyList()) + buildGuidance(
            surface = surface,''',
"guidance warning")
q=one(q,
'''            report = report
        )

        return PrecisionScanQuality(''',
'''            report = report
        )).distinct().take(3)

        return PrecisionScanQuality(''',
"guidance close")

s=one(s,
'''                ball = marks.first,
                cup = marks.second
            )
        precisionCurrentQuality?.let''',
'''                ball = marks.first,
                cup = marks.second,
                temporalCheckVerified = temporalResult.verified && !temporalResult.unstable
            )
        precisionCurrentQuality?.let''',
"feed temporal result")

if "Precision 7.4" not in s: raise SystemExit("v7.5 missing v7.4")
s=s.replace("Precision 7.4","Precision 7.5")
g=one(g,'versionName = "7.4"','versionName = "7.5"',"version name")
g=one(g,'versionCode = 740','versionCode = 750',"version code")

policy=root/"precision/PrecisionTemporalQualityGate.kt"
policy.write_text('''package jp.example.greenreader.precision

/** Conservative status presentation; not an accuracy calibration. */
object PrecisionTemporalQualityGate {
    fun score(rawScore: Int, temporalVerified: Boolean): Int {
        val bounded = rawScore.coerceIn(0, 100)
        return if (temporalVerified) bounded else bounded.coerceAtMost(84)
    }
}
''',encoding="utf-8")
assert "MAX_USABLE_SLOPE_PERCENT = 12f" in (root/"precision/PrecisionSlopeAnalyzer.kt").read_text()
assert 'button("結果入力")' in s and 'bitmap = failureBitmap' in s
qpath.write_text(q,encoding="utf-8")
mainpath.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v7.5 temporal quality confidence guard")
