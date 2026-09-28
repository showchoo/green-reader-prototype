"""v5.9: prevent Precision point-cloud clipping before a distant cup."""
from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if s.count(old) != 1:
        raise SystemExit(f"v5.9 {label}: expected one target, got {s.count(old)}")
    s = s.replace(old, new, 1)

once(
    "import jp.example.greenreader.precision.PrecisionMarkerCandidateGate\n",
    "import jp.example.greenreader.precision.PrecisionMarkerCandidateGate\n"
    "import jp.example.greenreader.precision.PrecisionDepthRangePolicy\n",
    "range policy import"
)

once(
    "    private val precisionCollector = PrecisionDepthCollector()\n",
    "    private val precisionCollector = PrecisionDepthCollector()\n"
    "    @Volatile private var precisionScanMaxDepthM = 5.0f\n",
    "range state"
)

old = '''                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)
                    precisionCollector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)
                    maybeAutoFinishScan()
'''
new = '''                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)

                    // The old fixed 5 m ceiling clipped the far end of longer
                    // putts. Example field log: Ball camera distance ~2.96 m,
                    // Cup ~5.74 m, and the extracted surface stopped at 2.1-2.4 m
                    // along a 3.16 m putt. Size the ceiling from the currently
                    // tracked Ball/Cup geometry, with a small margin and 12 m cap.
                    val cameraT = f.camera.pose.translation
                    val ballT = referenceAnchor.pose.translation
                    val cupT = cupAnchor
                        ?.takeIf { it.trackingState == TrackingState.TRACKING }
                        ?.pose?.translation
                    precisionScanMaxDepthM = PrecisionDepthRangePolicy.maxDepthM(
                        Vec3(cameraT[0], cameraT[1], cameraT[2]),
                        Vec3(ballT[0], ballT[1], ballT[2]),
                        cupT?.let { Vec3(it[0], it[1], it[2]) }
                    )
                    precisionCollector.integrate(
                        f,
                        referenceAnchor.pose,
                        pixelStrideStep = 4,
                        maxDepthM = precisionScanMaxDepthM
                    )
                    maybeAutoFinishScan()
'''
once(old, new, "dynamic collector depth")

# Include the effective ceiling in every window diagnostic without changing
# SurfaceBuilder or SlopeAnalyzer thresholds.
once(
    '        precisionWindowDiagnostics += windowDiagnostic\n',
    '        precisionWindowDiagnostics += windowDiagnostic + " depthMax=" + String.format("%.2f", precisionScanMaxDepthM)\n',
    "window depth diagnostic"
)

if s.count('appVersion = "Precision 5.8"') != 1:
    raise SystemExit("v5.9 app version target missing")
s = s.replace('appVersion = "Precision 5.8"', 'appVersion = "Precision 5.9"', 1)

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "5.8"') != 1 or g.count('versionCode = 580') != 1:
    raise SystemExit("v5.9 Gradle version target missing")
g = g.replace('versionName = "5.8"', 'versionName = "5.9"', 1)
g = g.replace('versionCode = 580', 'versionCode = 590', 1)

assert "maxDepthM = precisionScanMaxDepthM" in s
assert "PrecisionDepthRangePolicy.maxDepthM(" in s
assert "depthMax=" in s

p.write_text(s, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v5.9 dynamic scan depth ceiling")
