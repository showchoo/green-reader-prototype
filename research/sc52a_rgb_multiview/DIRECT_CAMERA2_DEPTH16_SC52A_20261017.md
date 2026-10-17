# S20+ SC-52A: direct Camera2 DEPTH16 acquisition research (v11.0)

## Real device discovery, 2026-10-17 21:50 JST

The user's independent v10.9 hardware-capture ZIP `Session_HW_20261017_215015_767.zip` (via the existing user-authorized Drive backup) contains the actual Samsung **SC-52A, API 33** Camera2 characteristics:

| Property | Observed |
|---|---|
| Public Camera2 camera IDs | 0, 1, 2, 3, **4** |
| Public DEPTH_OUTPUT / DEPTH16 candidate | **ID 4**, facing **back** |
| Camera4 hardware level | LIMITED |
| Camera4 DEPTH16 image sizes | **640×480**, **320×240** |
| Depth-exclusive output | **true** |
| Camera intrinsics and lens pose reported | **present** |
| Hardware discovery errors | **zero** |
| Direct Camera2 DEPTH16 frame successfully acquired yet? | **Not yet tested** |
| Camera4 guaranteed physical ToF sensor identity? | **Unproven** |
| Proven accurate green surface grade? | **No** |

This is a different **public Android Camera2 depth output path** from ARCore fused Depth. A directly usable range signal is promising, but **Camera2 may internally postprocess or fuse sensors**, and public DEPTH16 alone never certifies millimetre-level ground heights.

Android standard `ImageFormat.DEPTH16`: packed 16-bit sample = **low 13 bits radial distance in millimeters** and **high 3 bits confidence code**. Confidence code **0 = 100%**, **1 = 0%**, **2–7 = (code−1)/7**. Device depth-exclusive setting means do not simultaneously request color and depth from the same camera. See https://developer.android.com/reference/android/graphics/ImageFormat and https://developer.android.com/reference/android/hardware/camera2/CameraMetadata#REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT.

## What the research APK does

- Adds **MENU → Camera2深度画像を実際に取得（研究）**; launches a separate Android activity. The previous ARCore activity is paused, so the camera streams are not competing.
- The research screen requires a deliberate **深度データ取得開始** button. Point the rear phone at a stationary, textured floor; do not move it during this initial capture. A background Camera2 stream is opened *only* for DEPTH16.
- Selects only cameras that advertise `DEPTH_OUTPUT` and list `ImageFormat.DEPTH16`. Selects a bounded size no greater than 640×480 (SC-52A camera ID4 should choose 640×480).
- Uses `ImageReader` plus a bounded 12-frame capture, auto-closes the camera and ImageReader at 12 frames or at a 15-second watchdog deadline, captures `Sensor.TYPE_GRAVITY` timestamps when available.
- Decodes physical packed 16-bit pixels row-by-row honoring Camera2 `rowStride`, `pixelStride` and native byte order. The saved binary is normalised **little-endian row-major packed 16-bit**, NOT silently converted to an unsupported 8-bit grayscale image.
- Preserves raw sample confidence; records per-frame nonzero coverage, high-confidence coverage, range minimum/median/maximum, image and gravity timestamps, intrinsics, lens pose, distortion, sensor reference and depth-exclusive flag.
- Saves a private owned `Session_HW_DEPTH_.../Putt_000/Scan_01_DEPTH16` folder under Downloads/GreenReaderRecords and queues the *existing* opt-in Google Drive backup. Even a 0-frame failure is saved with a diagnostic report.
- Existing ARCore Depth slope estimation, RGB research recorder, putting UI and confidence safeguards are **unchanged**. v11.0 is **not** marketed as precise.

## Expected ZIP structure

```
Putt_000/Scan_01_DEPTH16/camera2_calibration.json
Putt_000/Scan_01_DEPTH16/depth_0001.bin
...
Putt_000/Scan_01_DEPTH16/depth_0012.bin
Putt_000/Scan_01_DEPTH16/camera2_depth_frames.csv
Putt_000/Scan_01_DEPTH16/camera2_gravity.csv
Putt_000/Scan_01_DEPTH16/camera2_depth_summary.json
Putt_000/Scan_01_DEPTH16/record_identity.json
```

The independent `inspect_camera2_depth16.py` parser detects valid physical-range pixels, confidence fraction, central distance repeatability, missing frames, malformed formats and absent calibration. A return of `DIRECT_DEPTH16_RANGE_FRAMES_CAPTURED` certifies **only direct distance data presence**, never slope/putting accuracy.

## Next gate

**Once** the new APK is signed and CI is green, the user only needs to do the one-touch, stationary floor capture. If direct DEPTH16 range images are valid, next calculate sensor-to-camera and gravity registration with independent physical level/rise reference before any new physical-grade claims. If Camera2 fails to open or produces no nonzero depth on the SC-52A firmware, diagnose error codes first; do not ask for another blind scan or a new phone.

## Privacy and release boundary

Only aggregate metadata or synthetic tests are committed to public GitHub. Do not publish private range maps, photos, room layouts, or full Session ZIPs. Do not merge depth data into commercial putting guidance without externally measured median grade error <=0.5pp and worst <=1.0pp and repeat spread <=0.5pp.
