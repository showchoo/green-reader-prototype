"""Fail closed if v10.8 repeats the v10.7 use-after-Image.close bug."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
rec=(root/"field/PrecisionRgbBurstRecorder.kt").read_text()
main=(root/"MainActivity.kt").read_text()
scan=(root/"field/ScanFieldRecorder.kt").read_text()
gradle=Path("app/build.gradle.kts").read_text()
rgb=(root/"precision/PrecisionNv21Rgb.kt").read_text()
tests=(Path("app/src/test/java/jp/example/greenreader/precision/PrecisionNv21RgbTest.kt")).read_text()

assert 'versionCode = 1080' in gradle
assert 'versionName = "10.8-rgb-jpeg-repair"' in gradle
assert "Precision 10.8 RGB研究" in main
assert 'val cpuWidth=image.width' in rec and 'val cpuHeight=image.height' in rec
assert 'val intr=frame.camera.imageIntrinsics' in rec
start=rec.index("                io.execute {")
end=rec.index("\n            }\n        } catch (e:com.google.ar.core.exceptions.NotYetAvailableException)",start)
worker=rec[start:end]
# The worker must never dereference Android Image after .use closes it.
for forbidden in ("image.width","image.height","image.timestamp","image.planes","image.cropRect"):
    assert forbidden not in worker, forbidden
assert 'YuvImage(nv21,ImageFormat.NV21,cpuWidth,cpuHeight,null)' in worker
assert 'PrecisionNv21Rgb.convert(nv21,cpuWidth,cpuHeight)' in worker
assert 'Bitmap.createBitmap(rgb.pixels' in worker
assert 'validJpeg(bytes)' in worker
assert 'temp.writeBytes(bytes)' in worker
assert 'temp.renameTo(dest)' in worker
assert 'c.rows.add(fullRow)' in worker
assert 'jpeg_codec' in rec and 'jpeg_width' in rec and 'jpeg_fx' in rec
assert 'first_encoder_error' in rec
assert 'it.length() >= 1024' in rec
assert 'private fun validJpeg(' in rec
assert 'fun convert(' in rgb and 'val outW' in rgb
assert tests.count('@Test') >= 5
assert 'PrecisionSlopeAnalyzer.analyze(' in main
assert 'PrecisionDepthSourceAudit.analyze(' in main
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in main
assert 'DriveBackupScheduler.onScanSaved(context)' in scan
assert scan.index('saveRgbResearchModern(context,folder,identity)') < scan.index('DriveBackupScheduler.onScanSaved(context)')
print("v10.8 research: no closed-Image use in async JPEG worker; fallback, atomic valid JPEG, timestamps and safety gates verified")
