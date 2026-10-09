"""v9.1: archive marker/Depth height discrepancy, cap overconfident quality.

Does not alter the slope, point cloud, fit, AR coordinates or saved field
schema. Uses already accepted ground cells and explicitly leaves sparse scans
inconclusive. A disagreement fails confidence presentation closed.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
def one(old,new,name):
    global s
    n=s.count(old)
    if n!=1: raise SystemExit(f"v9.1 {name}: expected 1, found {n}")
    s=s.replace(old,new,1)

one('''    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null''',
'''    private var precisionCurrentQuality: jp.example.greenreader.precision.PrecisionScanQuality? = null
    private var precisionMarkerDepthDisagreement = false''',
"state")
reset_old = '''        precisionCurrentQuality = null
        precisionCompletedDiagnostic = ""
        precisionLastScanFailed = false'''
reset_new = '''        precisionCurrentQuality = null
        precisionMarkerDepthDisagreement = false
        precisionCompletedDiagnostic = ""
        precisionLastScanFailed = false'''
if s.count(reset_old) != 3:
    raise SystemExit(f"v9.1 expected 3 reset points, got {s.count(reset_old)}")
s = s.replace(reset_old, reset_new)
one('''        precisionCurrentQuality =
            jp.example.greenreader.precision.PrecisionQualityEstimator.evaluate(''',
'''        // The ground-cell heights are observational and not truth data.
        // Compare them to the AR anchor delta before presenting HIGH confidence.
        val markerDepthCheck =
            jp.example.greenreader.precision.PrecisionMarkerDepthHeightAudit.evaluate(
                aggregateSurface, marks.first, marks.second
            )
        precisionMarkerDepthDisagreement = !markerDepthCheck.trustForQuality
        precisionLastDiagnostic += " | " + markerDepthCheck.summary()
        precisionCurrentQuality =
            jp.example.greenreader.precision.PrecisionQualityEstimator.evaluate(''',
"cross-check before quality")
one('''markerGeometryTrusted = precisionMarkerGeometry()?.needsReview != true''',
'''markerGeometryTrusted =
                    precisionMarkerGeometry()?.needsReview != true &&
                    !precisionMarkerDepthDisagreement''',
"quality gating")
one('''                "\\nDepth Raw=" + q.rawAcceptedFrames + " Full=" + q.fullAcceptedFrames +
                " / 絶対精度は未検証"''',
'''                "\\nDepth Raw=" + q.rawAcceptedFrames + " Full=" + q.fullAcceptedFrames +
                " / 絶対精度は未検証" +
                (if (precisionMarkerDepthDisagreement)
                    "\\n⚠ AR目印の高低差とDepth地面形状が矛盾"
                 else "")''',
"visible warning")
if s.count('Precision 9.0')<2:
    raise SystemExit("v9.1 previous version labels missing")
s=s.replace('Precision 9.0','Precision 9.1')
if g.count('versionName = "9.0"')!=1 or g.count('versionCode = 900')!=1:
    raise SystemExit("v9.1 Gradle version mismatch")
g=g.replace('versionName = "9.0"','versionName = "9.1"')
g=g.replace('versionCode = 900','versionCode = 910')
assert 'button("次のパット")' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'PrecisionDepthSourceAudit.analyze(' in s
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v9.1: marker/Depth height conflict logged and confidence capped; slope unchanged")
