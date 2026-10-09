"""v9.7: make 8-window scan failure actionable using real measured diagnostics.

Do not loosen fit thresholds, change point positions, or promote failures
to successes. The recorded failure reason includes a stable machine code.
"""
from pathlib import Path

main=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

old='''                recordPrecisionScanFailure("追加測定しても結果が安定しませんでした。もう一度スキャンしてください")'''
new='''                val failureAdvice =
                    jp.example.greenreader.precision.PrecisionScanFailureAdvisor.evaluate(
                        precisionCurrentQuality
                    )
                precisionLastDiagnostic += " | " + failureAdvice.diagnostic()
                recordPrecisionScanFailure(failureAdvice.message())'''
if s.count(old) != 1:
    at=s.find("追加測定しても")
    places=[(k,s[max(0,k-190):k+220]) for k in range(len(s)) if s.startswith("recordPrecisionScanFailure(",k)]
    raise SystemExit("v9.7 8-window failure target " + str(s.count(old)) + 
        "; generic phrase=" + str(at) +
        "; snippet=" + repr(s[max(0,at-210):at+240]) +
        "; calls=" + repr(places[:14]))
s=s.replace(old,new,1)
if s.count("Precision 9.6")<2:raise SystemExit("v9.7 previous version missing")
s=s.replace("Precision 9.6","Precision 9.7")
if g.count('versionName = "9.6"')!=1 or g.count("versionCode = 960")!=1:
    raise SystemExit("v9.7 version not v9.6")
g=g.replace('versionName = "9.6"','versionName = "9.7"')
g=g.replace("versionCode = 960","versionCode = 970")
assert "val precisionMaxWindows = 8" in s
assert "if (combined == null)" in s
assert 'recordPrecisionScanFailure(failureAdvice.message())' in s
assert "PrecisionMarkerDepthHeightAudit.evaluate(" in s
assert "PrecisionRepeatScanRecovery.decide(" in s
assert "PrecisionMotionEvidenceGate.evaluate(" in s
assert "DriveBackupScheduler.onScanSaved(context)" in (
    Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt")
).read_text()
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v9.7 failure reason classified, saved, and shown (fit criteria unchanged)")
