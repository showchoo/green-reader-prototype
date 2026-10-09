"""Green Reader v9.4: no false high-confidence floor/Depth results.

Field evidence 2026-10-09 v9.3: 19 scans / 6 successes, same-putt grade
reversal -8.84 -> +7.43 percentage points; a 3.116cm discrepancy was
mistakenly labeled CONSISTENT by the old 4cm guard.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
p=root/"MainActivity.kt"
g=Path("app/build.gradle.kts")
s=p.read_text(encoding="utf8")
grad=g.read_text(encoding="utf8")
def one(old,new,why):
    global s
    n=s.count(old)
    if n!=1: raise SystemExit("v9.4 "+why+" expected 1, saw "+str(n))
    s=s.replace(old,new,1)

one('''    private var precisionMarkerDepthDisagreement = false''',
'''    private var precisionMarkerDepthDisagreement = false
    private var precisionSamePuttConflict = false
    private var precisionSamePuttSlopesPuttId = -1
    private val precisionSamePuttSlopeHistory = ArrayList<Pair<Float, Float>>(16)''',
"same-putt state")
old='''        precisionMarkerDepthDisagreement = false
        precisionCompletedDiagnostic = ""'''
new='''        precisionMarkerDepthDisagreement = false
        precisionSamePuttConflict = false
        precisionCompletedDiagnostic = ""'''
count=s.count(old)
if count!=3: raise SystemExit("v9.4 reset count expected 3 got "+str(count))
s=s.replace(old,new)

anchor='''        precisionCurrentQuality?.let { quality ->'''
one(anchor,'''        // Compare completed results at the same physical marker locations.
        // This catches strong sign flips between scans, which an intra-scan
        // temporal consistency gate alone cannot see.
        if (precisionSamePuttSlopesPuttId != precisionPuttId) {
            precisionSamePuttSlopesPuttId = precisionPuttId
            precisionSamePuttSlopeHistory.clear()
        }
        val reportedPuttSlope = combined?.let {
            Pair(it.overallLongitudinalPercent, it.overallCrossPercent)
        }
        val samePuttCheck =
            jp.example.greenreader.precision.PrecisionSamePuttAudit.evaluate(
                precisionSamePuttSlopeHistory, reportedPuttSlope
            )
        precisionSamePuttConflict = samePuttCheck.blocksDirection
        if (reportedPuttSlope != null && reportedPuttSlope.first.isFinite() &&
            reportedPuttSlope.second.isFinite()) {
            precisionSamePuttSlopeHistory.add(reportedPuttSlope)
        }
        val trustVerdict = precisionCurrentQuality?.let {
            jp.example.greenreader.precision.PrecisionScanConfidenceGuard.apply(
                it, markerDepthCheck, samePuttCheck
            )
        }
        if (trustVerdict != null) {
            precisionCurrentQuality = trustVerdict.quality
            if (trustVerdict.blocksDirection) precisionDirectionTrustworthy = false
            precisionLastDiagnostic += " | " + trustVerdict.summary()
        }
        precisionLastDiagnostic += " | " + samePuttCheck.summary()
        updatePrecisionRecordLabel()

        precisionCurrentQuality?.let { quality ->''',
"compare prior accepted scans before quality frozen")

oldmsg=r'''                (if (precisionMarkerDepthDisagreement)
                    "\n⚠ AR目印の高低差とDepth地面形状が矛盾"
                 else "")'''
newmsg=r'''                (if (precisionMarkerDepthDisagreement)
                    "\n⚠ AR目印の高低差とDepth地面形状が矛盾"
                 else "") +
                (if (precisionSamePuttConflict)
                    "\n⚠ 同じパットの傾斜方向が前回と矛盾。ライン判定を保留"
                 else "")'''
one(oldmsg,newmsg,"visible conflicting same-putt guidance")

if s.count("Precision 9.3")<2:raise SystemExit("v9.4 previous app version not found")
s=s.replace("Precision 9.3","Precision 9.4")
if grad.count('versionName = "9.3"')!=1 or grad.count("versionCode = 930")!=1:
    raise SystemExit("v9.4 gradle 9.3 not found")
grad=grad.replace('versionName = "9.3"','versionName = "9.4"')
grad=grad.replace('versionCode = 930','versionCode = 940')
assert 'precisionFramePoseScanSummary()' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in s
p.write_text(s,encoding="utf8")
g.write_text(grad,encoding="utf8")
print("v9.4: fail-closed confidence + real same-putt sign flip diagnostics applied")
