"""Regression guard for Green Reader Precision v7.1 automatic field packages."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf-8")
recorder = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt").read_text(encoding="utf-8")
gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")

assert 'versionName = "7.1"' in gradle and 'versionCode = 710' in gradle
assert 'appVersion = "Precision 7.1"' in main
assert "precisionFieldSessionId" in main
assert "precisionPuttId = 1" in main
assert "precisionScanIndex += 1" in main
assert "ScanFieldRecorder.saveGrouped(" in main
assert "ScanFieldRecorder.saveFailureGrouped(" in main
assert "android.view.PixelCopy.request(" in main
assert "android.view.PixelCopy.SUCCESS" in main
assert "failureBitmap" in main
assert "failureBitmap: Bitmap? = null" in recorder
assert recorder.count('"camera.jpg"') >= 3
assert 'Session_$session/$putt/' in recorder
assert "record_identity.json" in recorder
assert "scan_quality.json" in recorder
print("Precision v7.1 automatic field package checks passed")
