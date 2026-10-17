# SC-52A v11.0 fixed-mount reassessment: TYPE_GRAVITY is NOT verified physical camera movement

**User's direct clarification:** The Galaxy S20+ position and angle **were not moved** throughout the October 18, 2026 A=level, B=raised, C=level, D=raised experiment. The analysis must honor that reported mechanical condition and must not describe the 1.2° TYPE_GRAVITY difference as observed or proven phone motion.

## Evidence verified again from the user's four private Camera2 ZIPs

All four scans: Camera2 ID 4, DEPTH16 640×480; 11 usable depth frames of 12; matching calibration constants; no acquisition errors. The v11.0 archive records **Sensor.TYPE_GRAVITY only**, not the independent raw `TYPE_ACCELEROMETER` or `TYPE_GYROSCOPE` measurements.

| Pair | Median full-record gravity angle difference | **last 50-sample settled** gravity angle | Depth difference median in predeclared candidate static-right ROI x530..625 y100..370 |
|---|---:|---:|---:|
| A level → B raised | ~0.031° | **0.017°** | **0mm**, 10th–90th percentile −2..+2mm |
| C level → D raised | ~0.031° | **0.018°** | **0mm**, 10th–90th percentile −2..+2mm |
| A level ↔ C level | ~1.227° | **1.222°** | **+3mm**, 10th–90th percentile −1..+6mm |
| B raised ↔ D raised | ~1.238° | **1.232°** | **+3mm**, 10th–90th percentile −1..+6mm |

The candidate right-side background has depth support at 100% of pixels considered. It was designated by geometrical stability but was **not independently identified as a physically unchanged surface**; an apparently stable distance cannot prove zero camera rotation.

The first Android gravity reading of each scan differs from the final-50-sample median by A **0.600°**, B **0.273°**, C **0.161°**, D **0.842°**. Despite this startup convergence, the tail of each capture is very internally consistent (maximum instantaneous deviation of last 50 readings from tail median: **0.017°, 0.010°, 0.013°, 0.018°**, respectively). Each scan's TYPE_GRAVITY vector norm remains approximately **9.8066502 m/s²** at every sample, suggesting it reports a normalised/fused gravity estimate, not independent gravity acceleration noise.

## Interpretation and explicit limit

Android defines `TYPE_GRAVITY` as a **processed gravity direction and magnitude**, sourced from accelerometer and (when available) gyro. Authoritative documentation: https://source.android.com/docs/core/interaction/sensors/sensor-types .

- **Physical camera motion is NOT established.** User reports unchanged mount. ~1.22° is a difference in the *reported gravity reference*, which is inconsistent with the fixed-device experimental condition.
- **Cause still undecidable from the stored sensors.** The first several samples of TYPE_GRAVITY have a clear settling transient, but even the stable tail from A versus C differs. Plausible hypotheses include gyro/accelerometer fusion reset/bias, camera platform/support microslip (not deliberately adjusted), temperature/calibration effects, or scene/depth processing changes. The current ZIPs lack raw accelerometer, raw gyro, inertial bias or calibrated independently stationary visual fiducials to establish which.
- Gravity offset must **not** be subtracted as a true rotation from a physical slope or used to declare a movement failure. Depth-derived background normals also change across the separated groups; cannot assign causality with the present depth-only captures.
- The two level→raised *within-group* comparisons remain A→B and C→D, without inserting the nominal between-group gravity change into the incline target.
- No new scan, APK purchase or device replacement is warranted solely by this conflict. The next instrumentation change, **if independently measured grade testing resumes**, should record unsmoothed accelerometer and gyro simultaneously with gravity plus timestamp and sensor/vendor metadata, calibrating the true physical camera-to-IMU transform before using it for absolute slope.

**Final R&D state: TYPE_GRAVITY reference inconsistent across sessions under operator-reported fixed mounting; physical 2% grade accuracy NOT CERTIFIED; user statement of no camera adjustment accepted.** All per-pixel room depth and raw sensor ZIPs remain in user's private Drive, never public GitHub.
