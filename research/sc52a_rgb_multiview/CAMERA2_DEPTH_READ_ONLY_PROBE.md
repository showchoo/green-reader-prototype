# Galaxy S20+ SC-52A — read-only Camera2 depth-capability probe (v10.9)

**Purpose:** determine whether Android's **public Camera2 API** exposes a `DEPTH16` output on this **specific** SC-52A firmware, before spending more time on the ARCore Depth/RGB non-identifiable slope problem. This is a hardware capability check, NOT an accurate green-reading algorithm.

## Evidence motivating this probe

The user's v10.8 research session from 2026-10-17 successfully recorded 22/22 usable CPU RGB frames and 915 inertial samples. The camera traveled 24cm. Multi-view reconstruction found thousands of candidate correspondences, but the absolute grade remained unidentifiable: models constrained to different physical slopes could all fit held-out images with approximately 0.58–0.71 pixels of image reprojection error. ARCore Depth displayed +7.83%; neither algorithm certified actual ground grade. See `REAL_SC52A_RGB_RESULT_20261017.md`.

S20+ may contain a ToF camera, but this does **not** prove that Android permits a third-party app to get independent raw ToF measurements. Google ARCore Depth output can differ from direct hardware depth.

Android's official `CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT` API describes public Camera2 depth capability and its mandatory `ImageFormat.DEPTH16`. Vendor-specific/hardware-hidden cameras may not appear. The only supported answer is the **device's own actual characteristics**. Official: https://developer.android.com/reference/android/hardware/camera2/CameraMetadata#REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT and https://developer.android.com/reference/android/hardware/camera2/CameraManager#getCameraCharacteristics(java.lang.String).

## What v10.9 adds

In MENU: **ToF / Camera2深度を確認・保存**.

One tap performs all of the following automatically, with no scanning and without requesting additional hardware:

1. Use `CameraManager.cameraIdList`, query each camera's `CameraCharacteristics`, and include physical camera IDs visible through logical Camera2 cameras.
2. Inspect advertised `DEPTH_OUTPUT`, supported `DEPTH16` and `DEPTH_POINT_CLOUD` output sizes, depth-exclusivity flag and existence of pose/intrinsics calibration metadata.
3. Never call `openCamera`; it is a read-only capability probe that does not interrupt ARCore or start another camera stream.
4. Save `camera2_capabilities.json` **plus completion marker** `record_identity.json` in an independent `Session_HW_.../Putt_000/Scan_01_CAMERA2` folder. This reuses the existing backup archive and can upload to the user's authorized Google Drive when opt-in backup is enabled.
5. Display an in-app result:
   - `PUBLIC_CAMERA2_DEPTH16`: at least one camera advertises depth output and enumerates DEPTH16 size. A **candidate** for a new modality, not proof of ToF or accuracy.
   - `NO_PUBLIC_CAMERA2_DEPTH16`: no enumerated camera exposes depth output, all queries succeeded; **not** proof the hardware ToF does not exist.
   - `INDETERMINATE`: missing access, failed query, or no cameras; never claim a negative from partial observations.

The existing RGB capture and Depth slope code, consent UI, scan processing, unit tests, signing certificate, data folders and background uploader are untouched except for adding this optional capability button and an independent hardware report saver.

## Gate before another APK

- CI tests generated v10.9 source, the four Camera2 classification cases, all existing Android unit tests, independent geometry regressions, APK signature SHA256 `2c06a12144ece069f117dc495c49a15e14108e61167ac9befddbfd4c60919fa0`, `versionCode=1090`.
- No private captured images or complete private Session ZIPs committed to the public repository.
- If an accessible DEPTH16 camera is found, **do not claim the sensor meets 5mm grade precision**. First build a separate permission-safe Camera2 image acquisition test and independently calibrate the physical floor.
- If none is exposed, **stop third-party Android Camera2-ToF development on this SC-52A firmware**, unless stronger evidence of vendor SDK access is found. Do not ask the user to buy a new phone.
- In either result, existing v10.8/v10.9 putting guidance remains unvalidated research output, not commercially precise aim assistance.
