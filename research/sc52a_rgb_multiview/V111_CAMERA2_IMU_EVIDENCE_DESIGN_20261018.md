# Green Reader Precision v11.1 — Camera2 DEPTH16 + raw IMU evidence

## Why this change

Four depth-only sessions on the user-owned SC-52A Galaxy S20+ were explicitly captured in the order **level → inclined → level → inclined**, with the user confirming that the physical phone mount was **never moved**. Existing v11.0 files contained Android's already-processed `TYPE_GRAVITY`, and analysis found about **1.23°** direction differences between the two level captures. This is **not proof of 1.23° phone rotation**: no independent physical pose reference and no simultaneous raw gyro/accelerometer traces were stored.

This branch adds **evidence only**; no application putting-line/cup calculations change. **No physical grade or camera orientation is certified.**

## Added research-only recording

The separate Camera2 `Camera2DepthCaptureActivity` now starts sensor registration as soon as the user explicitly presses **深度データ取得開始**, before opening Camera2, to observe initial Android gravity-filter settling.

The same `HandlerThread` receives asynchronous Camera2 image and sensor callbacks; all stored sensor samples include BOTH `SensorEvent.timestamp` and `SystemClock.elapsedRealtimeNanos()` sampled in the callback. These are two distinct quantities and must not be confused with image capture timestamps.

Sampled streams:

- Android `TYPE_GRAVITY` (processed direction/gravity vector; retains the exact legacy CSV).
- Android `TYPE_ACCELEROMETER` (calibrated acceleration, includes gravity and motion; **not raw uncalibrated accelerometer**).
- Android `TYPE_GYROSCOPE` (calibrated angular rates, not integrated world orientation).
- If exposed: `TYPE_GYROSCOPE_UNCALIBRATED` (angular velocity + factory bias estimate). If absent, the other streams are still saved with explicit availability flags.

`camera2_sensor_events.csv` columns:

```
sensor_type,sensor_timestamp_ns,callback_elapsed_ns,x,y,z,bias_x,bias_y,bias_z,accuracy
```

Records are bounded to 3,600 samples per sensor, with invalid, duplicate/out-of-order and buffer-cap overflow counters in `camera2_sensor_metadata.json`; all per-type registration results are also explicit. Saved format continues to include **all old v11.0 files and filenames**. Per depth-frame `callback_elapsed_ns` is appended to its CSV (without removing any columns), distinguishing image arrival from image capture time.

The **clock-domain safeguard** is vital: when `CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE` is **REALTIME**, Camera2 Image timestamps share the `elapsedRealtimeNanos` time base and can be aligned with sensor event timestamps. If **UNKNOWN**, they cannot safely be combined as precise exposure-synchronized measurements. The Android docs explicitly distinguish these cases:
https://developer.android.com/reference/android/hardware/camera2/CameraMetadata#SENSOR_INFO_TIMESTAMP_SOURCE_UNKNOWN

`audit_depth16_imu_evidence.py` validates saved ZIP structure, monotonic sensor and frame timestamps, sample-count checks, per-stream first-vs-last vector changes, and whether raw gyro/accelerometer traces span depth acquisition. It does not convert gyroscope rates into independent surveyed tilt or assign a board ROI.

## Compatibility and limits

- Application package ID unchanged, versionCode **1110** vs v11.0 **1100**.
- Same approved app certificate is required for in-place update; CI verifies SHA-256 against v11.0's published certificate.
- Camera2 depth camera access still bounded at twelve frames / 15-second watchdog. No continuous background sensing; listeners are unregistered on capture finish.
- The existing ARCore surface analysis, putt-line math and drive user-opt-in flow are untouched.
- Only capture sessions created by the user with the research button contain the added IMU fields. Old v11.0 ZIPs still work with their previous auditor and do NOT magically gain accelerometer/gyro data.
- This is not yet a fix for missing **verified board ROI**, independent actual rise/run, yaw, camera-to-gravity extrinsics, or depth calibration bias. Do not imply sub-0.5 percentage-point real-world precision.

## Validation

`Camera2SensorEvidenceTest.kt` synthetic JVM tests guard CSV schema, six-axis uncalibrated gyro bias values, per-sensor buffer caps, out-of-order timestamps and invalid vectors. `test_audit_depth16_imu_evidence.py` tests both valid REALTIME and deliberately noncomparable UNKNOWN Camera2 timebase, absent gyro and legacy v11.0 ZIP handling.

CI executes the original v11.0 patch-generator and all verification *before* changing version to v11.1, compiles/debug-unit-tests the signed Android APK, confirms versionCode and verifies the original installed-app compatible certificate.

## What further data would mean

Only after a user explicitly chooses to install this **research build**, a new fixed-mount Camera2 capture may reveal whether the previously observed 1.23° gravity difference coincides with real gyro angular displacement, accelerometer motion, sensor filter startup, or a clock-domain issue. It **cannot** retroactively repair earlier archives or independently prove exact physical phone stillness. No new repetitive field testing should be requested until a targeted comparison with a valid physical reference has been designed.
