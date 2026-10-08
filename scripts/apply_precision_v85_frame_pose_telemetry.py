"""v8.5 observational telemetry: Depth timestamp + camera-frame pose.

This appends a small bounded CSV section to the collector diagnostic already
saved on successful and failed scans. No slope, fit, sampling, or quality
decision changes. Note: camera pose is sampled from the current ARCore Frame;
the depth image timestamp can differ. Keep both and investigate latency.
"""
from pathlib import Path
import re

root = Path("app/src/main/java/jp/example/greenreader")
collector = root / "precision/PrecisionDepthCollector.kt"
main = root / "MainActivity.kt"
gradle = Path("app/build.gradle.kts")
c=collector.read_text(encoding="utf8")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
def one(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit(f"v8.5 {label}: expected 1 occurrence, found {n}")
    return src.replace(old,new,1)

c=one(c,
'''    private val samples = ArrayList<PrecisionDepthPoint>(70000)''',
'''    private val samples = ArrayList<PrecisionDepthPoint>(70000)
    private val framePoseTelemetry = PrecisionFramePoseTelemetry.Buffer()''',
"telemetry buffer")
c=one(c,
'''        samples.clear()
        frameTimestamps.clear()''',
'''        samples.clear()
        framePoseTelemetry.clear()
        frameTimestamps.clear()''',
"scan reset")
c=one(c,
'''    @Synchronized fun snapshot(): List<PrecisionDepthPoint> = samples.toList()''',
'''    @Synchronized fun snapshot(): List<PrecisionDepthPoint> = samples.toList()
    @Synchronized fun framePoseDiagnostics(): String =
        framePoseTelemetry.toDiagnosticText()''',
"pose diagnostics snapshot")
c=one(c,
'''        if (added > 0) {
            frameTimestamps += timestamp''',
'''        if (added > 0) {
            // Camera pose uses the current AR Frame time; Depth image time
            // can be older. Preserve BOTH timestamps for later bias analysis.
            val cameraLocal = levelFrame.worldToLocal(camera.pose.translation)
            val q = camera.pose.rotationQuaternion
            framePoseTelemetry.record(
                PrecisionFramePoseTelemetry.Entry(
                    depthTimestampNs = timestamp,
                    cameraFrameTimestampNs = frame.timestamp,
                    source = if (isRaw) "raw" else "full",
                    x = cameraLocal[0], y = cameraLocal[1], z = cameraLocal[2],
                    qx = q[0], qy = q[1], qz = q[2], qw = q[3]
                )
            )
            frameTimestamps += timestamp''',
"accepted frames only")

# Capture the telemetry BEFORE each short scan-window collector reset.
# The app aggregates multiple collector windows into one persisted scan.
s=one(s,
'''    private val precisionTrackingMonitor =
        jp.example.greenreader.precision.PrecisionTrackingMonitor()''',
'''    private val precisionFramePoseWindows = ArrayList<String>(8)
    private val precisionTrackingMonitor =
        jp.example.greenreader.precision.PrecisionTrackingMonitor()''',
"multi-window pose state")
s=one(s,
'''        precisionCollectorWindowSnapshots += precisionCollector.diagnosticSnapshot()''',
'''        precisionCollectorWindowSnapshots += precisionCollector.diagnosticSnapshot()
        precisionFramePoseWindows += precisionCollector.framePoseDiagnostics()''',
"capture pose before each collector clear")
s=one(s,
'''    private fun precisionFieldCollectorSummary(): String {''',
'''    private fun precisionFramePoseScanSummary(): String {
        val poseSections = precisionFramePoseWindows.toMutableList()
        val active = precisionCollector.framePoseDiagnostics()
        if (!active.startsWith("FRAME_POSE_V1_BEGIN records=0 ")) {
            poseSections += active
        }
        return poseSections.joinToString("\\n")
    }

    private fun precisionFieldCollectorSummary(): String {''',
"aggregated pose helper")
reset=re.compile(r'(?m)^([ \t]*)precisionCollectorWindowSnapshots\.clear\(\)$')
s,reset_count=reset.subn(
    lambda m:m.group(0)+"\n"+m.group(1)+"precisionFramePoseWindows.clear()",s
)
if reset_count<1:
    raise SystemExit("v8.5 expected window-snapshot reset sites")

# Attach the aggregated short-window blocks only to the existing saved
# collector_diagnostics.txt, not the live status or quality gates.
pat=r'(collectorDiagnostic\s*=\s*)precisionFieldCollectorSummary\(\)'
repl=r'\g<1>precisionFieldCollectorSummary() + "\\n" + precisionFramePoseScanSummary()'
s,n=re.subn(pat,repl,s)
if n<2: raise SystemExit(f"v8.5 persisted collectorDiagnostic sites: got {n}, expected >=2")
if s.count("precisionFramePoseScanSummary()") != n+1:
    raise SystemExit("v8.5 pose diagnostics must appear only in save paths")
if s.count("Precision 8.4")<2:raise SystemExit("v8.5 missing generated v8.4 app version labels")
s=s.replace("Precision 8.4","Precision 8.5")
g=one(g,'versionName = "8.4"','versionName = "8.5"',"version name")
g=one(g,'versionCode = 840','versionCode = 850',"version code")
assert "PrecisionScaleDirectionAudit.evaluate(" in s
assert "PrecisionPairedFlankAudit.evaluate(" in s
assert "PrecisionDepthSourceAudit.analyze(" in s
assert 'button("結果入力")' in s and 'button("次のホール")' in s
assert 'precision_depth_sources.csv' in (root/"field/ScanFieldRecorder.kt").read_text()
collector.write_text(c,encoding="utf8")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print(f"Applied v8.5 camera pose telemetry (saved collector diagnostics paths={n})")
