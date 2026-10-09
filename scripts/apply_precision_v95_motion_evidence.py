"""Green Reader v9.5: cap high confidence without parallax evidence.

M07 v9.4 Putt_003 completed 3 scans with score=92..94 and
~0.03m per-scan camera movement, but user-described nearly flat
floor still measured ~2.5% longitudinal AND cross slope.
Stability does not imply true absolute accuracy.
"""
from pathlib import Path
main=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
g=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
v=g.read_text(encoding="utf8")
def one(old,new,label):
    global s
    n=s.count(old)
    if n!=1: raise SystemExit("v9.5 "+label+" expected 1 got "+str(n))
    s=s.replace(old,new,1)

one('''    private var precisionSamePuttConflict = false''',
'''    private var precisionSamePuttConflict = false
    private var precisionMotionHighCapped = false''',
"motion state")
reset='''        precisionSamePuttConflict = false
        precisionCompletedDiagnostic = ""'''
updated='''        precisionSamePuttConflict = false
        precisionMotionHighCapped = false
        precisionCompletedDiagnostic = ""'''
if s.count(reset)!=3: raise SystemExit("v9.5 expected 3 full scan resets got "+str(s.count(reset)))
s=s.replace(reset,updated)
one('''        precisionLastDiagnostic += " | " + samePuttCheck.summary()
        updatePrecisionRecordLabel()

        precisionCurrentQuality?.let { quality ->''',
'''        precisionLastDiagnostic += " | " + samePuttCheck.summary()
        precisionCurrentQuality?.let { current ->
            val motionCheck =
                jp.example.greenreader.precision.PrecisionMotionEvidenceGate.evaluate(current)
            precisionMotionHighCapped = motionCheck.cappedFromHigh
            precisionCurrentQuality = motionCheck.quality
            precisionLastDiagnostic += " | " + motionCheck.diagnostic()
        }
        updatePrecisionRecordLabel()

        precisionCurrentQuality?.let { quality ->''',
"motion guard before save and display")
one(r'''                (if (precisionSamePuttConflict)
                    "\n⚠ 同じパットの傾斜方向が前回と矛盾。ライン判定を保留"
                 else "")''',
r'''                (if (precisionSamePuttConflict)
                    "\n⚠ 同じパットの傾斜方向が前回と矛盾。ライン判定を保留"
                 else "") +
                (if (precisionMotionHighCapped)
                    "\n⚠ 端末移動が少ないため高信頼判定を保留"
                 else "")''',
"visible parallax warning")
if s.count("Precision 9.4")<2:raise SystemExit("v9.5 prior app label not found")
s=s.replace("Precision 9.4","Precision 9.5")
if v.count('versionName = "9.4"')!=1 or v.count("versionCode = 940")!=1:
    raise SystemExit("v9.5 previous version config missing")
v=v.replace('versionName = "9.4"','versionName = "9.5"')
v=v.replace("versionCode = 940","versionCode = 950")
assert 'DriveBackupScheduler.onScanSaved(context)' in Path(
    "app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt"
).read_text()
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
main.write_text(s,encoding="utf8")
g.write_text(v,encoding="utf8")
print("v9.5 no-false-high confidence gate with real camera travel diagnostics")
