"""v10.8 RGB Research: fix all 19 JPEGs being empty on Galaxy S20+.

The v10.7 async encoder dereferenced image.width/height after
Frame.acquireCameraImage().use had CLOSED the media.Image.
The worker opened FileOutputStream before using invalid Image dimensions,
thereby creating zero-byte JPEGs while dropping the frame metadata.

This patch advances only generated app version fields. Revised recorder,
pure NV21 software fallback and tests are checked into the repo directly.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
if m.count("Precision 10.7 RGB研究") < 2:
    raise RuntimeError("v10.8 needs generated v10.7 source")
m=m.replace("Precision 10.7 RGB研究","Precision 10.8 RGB研究")
if g.count('versionName = "10.7-rgb-research"') != 1:
    raise RuntimeError("v10.8 needs previous Gradle version")
if g.count('versionCode = 1070') != 1:
    raise RuntimeError("v10.8 needs previous versionCode")
g=g.replace('versionName = "10.7-rgb-research"',
            'versionName = "10.8-rgb-jpeg-repair"')
g=g.replace('versionCode = 1070','versionCode = 1080')
assert "PrecisionRgbBurstRecorder.capture(" in m
assert "PrecisionSlopeAnalyzer.analyze(" in m
assert "PrecisionDepthSourceAudit.analyze(" in m
assert "PrecisionMarkerDepthHeightAudit.evaluate(" in m
assert "PrecisionAnchoredGroundSelector.select(" in (
    root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert "DriveBackupScheduler.onScanSaved(context)" in (
    root/"field/ScanFieldRecorder.kt").read_text()
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Precision v10.8 research: only generated version advanced; fixed JPEG recorder code checked in.")
