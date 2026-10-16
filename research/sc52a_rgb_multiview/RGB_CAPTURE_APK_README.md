# SC-52A RGB sequence recorder — research APK

## Why this exists

The S20+ v10.6 ARCore Raw/Full depth pipeline **failed the level-floor repeatability check**. The camera/Depth positional mismatch has not been explained. We are **not** shipping a putting-line accuracy improvement.

This v10.7 research build retains the existing signed Android package and v10.6 quality/fail-closed direction rules. It **adds an explicit opt-in** CPU RGB burst synchronized with the ARCore Frame and pose/IMU telemetry. The app can be installed as an update over v10.6 without clearing prior recordings. Signing compatibility is enforced in CI.

## UI

- Expand MENU and tap **研究RGB連続記録: OFF**.
- Read the consent dialog. Enabling allows up to **96 real camera JPEGs per scan**, plus calibration, pose, and inertial CSV files. The switch is off by default and stored persistently when enabled.
- If automatic Google Drive backup was already enabled, research photos will be included in the existing session ZIP on the user's own Drive. Turning RGB research off suppresses research capture on subsequent scans; Drive permissions remain independently controlled in Saved Data.
- Each normal Scan starts a separate research burst. It records even if numerical slope analysis later fails, provided a grouped failure record gets saved.

## Capture invariants

- ARCore `Frame.acquireCameraImage()` provides an actual CPU `YUV_420_888` color image corresponding to the current frame, not a screenshot of the GL overlay.
- Every captured image is closed promptly on the GL thread. It is converted to NV21 respecting individual row and pixel strides, then encoded to JPEG asynchronously.
- Capture is limited to **8 fps, maximum 96 images per scan**, with **at most 3 YUV images in flight**. Backpressure drops a frame rather than blocking indefinitely.
- CSV stores image time and frame time separately, plus Android camera clock, *current CPU image intrinsics*, current physical camera pose, Android sensor pose, and live ball/cup anchor positions.
- `rgb_imu.csv` stores monotonic timestamps and the raw accelerometer, gyro and gravity sensor samples if the sensor types are available. Camera-versus-sensor timestamp synchronization must still be **validated on-device**; do not assume all vendors share exactly the same reference epoch.
- The CSV preserves missing-pose columns (rather than shifting field positions) and explicitly records missing sensor values.
- RGB images are saved under the **same three-level** Session/Putt/Scan folder as the existing scan's other records; the backup archive rejects deeper paths, so no `rgb/` subfolder is added.
- Grouped successful/failed scan records append the burst **before** `DriveBackupScheduler.onScanSaved()`, ensuring debounced worker sees complete files.
- User camera photos remain private and are never checked into GitHub. Only the user-authorized Drive backup is used.

## Files in each completed Session ZIP

```
Putt_001/Scan_01_.../record_identity.json
Putt_001/Scan_01_.../camera.jpg
Putt_001/Scan_01_.../rgb_0001.jpg
Putt_001/Scan_01_.../rgb_0002.jpg
...
Putt_001/Scan_01_.../rgb_frames.csv
Putt_001/Scan_01_.../rgb_imu.csv
Putt_001/Scan_01_.../rgb_capture_status.json
```

**No hardware precision certification** is asserted. The CSV values come from ARCore VIO/inertial APIs and can still drift. A long sequence, high feature match count or large inferred camera translation are necessary conditions, *not* a proven 5mm ground-height measurement.

## Offline QA before visual 3D research

`python research/sc52a_rgb_multiview/inspect_rgb_sequence.py <user-authorized-session.zip>`

The research QA refuses to mark a capture as ready if:
- fewer than 12 usable image rows exist,
- the listed JPEGs are missing,
- timestamps are not increasing or diverge beyond 50ms,
- ARCore-derived observed camera translation baseline is below 12cm.

READY_FOR_OFFLINE_MULTIVIEW_ATTEMPT means **ready for further reconstruction analysis only**. It is never a physical-grade or product PASS.

## User-side test once the signed APK is available

No new equipment or phone is needed. In a well-lit nonreflective, textured indoor floor area, enable the opt-in switch and mark a single Ball/Cup pair about 0.8–1.0m apart. Run **one normal scan**, keeping the floor framed while translating the S20+ *sideways* approximately 20–30cm; do not merely rotate in place. Wait for the usual local session save and automatic Google Drive sync. Say `スキャンしました` and the assistant will retrieve/validate the ZIP. Avoid people, papers or private items in the camera's field of view.

If the initial capture is missing CPU frames, the research output will show a clear zero-frame/unavailable count rather than claim successful 3D measurement.

## Stop/go rule

One successful research ZIP only establishes that **synchronized RGB input exists**. The next offline analysis must estimate metric 3D with an independently known scale/gravity reference and demonstrate flat-floor grade accuracy, otherwise this approach cannot be offered as a replacement for hardware slope measurement. Do not weaken v10.6 direction gates or market this R&D APK as accurate until that evidence exists.

Official ARCore API reference: https://developers.google.com/ar/reference/java/com/google/ar/core/Frame
