# 2026-10-17 — Galaxy S20+ v10.8 real RGB scan: capture PASS, metric slope NO-GO

## Scope and provenance

- Device: **Samsung SC-52A (Galaxy S20+)**, Android API 33.
- User-uploaded authorized Google Drive session: `Session_20261017_211412_65222e51.zip`, folder `Putt_002/Scan_01_20261017_211508_468`; timestamp around 21:15 JST.
- Build: `Precision 10.8 RGB研究`, one nominal successful Depth slope analysis.
- Keep all users' JPEGs, room imagery, and full archived ZIP in private authorized storage. **Do NOT commit them to GitHub**. This document contains aggregate measurements only.
- Earlier indoor floor was checked with a spirit level. This session does not contain a quantified, independently surveyed rise/run or proof of exactly the same marked floor positions; treat absolute accuracy as **unknown**.

## Data-collection bug fixed — confirmed on real SC-52A

| Capture metric | Actual |
| --- | ---: |
| RGB CPU images attempted | 22 |
| Fully encoded and saved JPEGs | **22** |
| Zero-byte/invalid JPEGs | **0** |
| Encoder failure / dropped / unavailable | **0 / 0 / 0** |
| Native NV21 JPEG successes | **22** |
| Fallback Bitmap JPEG uses | **0** |
| Image size | 640x480 |
| Concurrent inertial sensor samples | **915** |
| Elapsed ARCore frame time | **3.733 seconds** |
| Max ARCore VIO-derived camera translation baseline | **24.02 cm** |
| Median CPU image timestamp minus ARCore frame timestamp | **+2.595 ms** |
| Median ARCore frame timestamp minus Android camera timestamp | **+25.066 ms** |

All 22 JPEGs decode successfully and image dimensions match saved intrinsics and manifest. The 25ms relationship between two ARCore/Android timestamps is an observation, **not an isolated cause** of reconstruction error; timestamp semantics differ and cannot be corrected by blind shifting.

## RGB metric stereo: a reconstruction attempt, not a physical certification

Saved image intrinsics: approximately `fx = 480.69 px`, `fy = 476.29 px`, `cx = 323.06 px`, `cy = 237.57 px` at 640x480.

- Across the 22 images, SIFT detects approximately **1,739–2,335** image features per frame in the original broad-feature diagnostic.
- Independent RANSAC image correspondences and ARCore VIO-initialized metric camera projection produce approximately **3,226 valid pairwise 3D candidate observations** across nine tested pairs. These are **not 3,226 independently surveyed 3D points**; the same floor features may appear in multiple pairs.
- Several pairs have subpixel epipolar residuals (roughly 0.23–0.46 pixels median for tested pairs), but geometric consistency **does not prove the reconstructed heights are accurate**.
- For the tested image-pair ground-plane regressions, **forward candidates vary approximately −3.22% to +2.76%**, depending on camera pair and floor region. The production ARCore-Depth slope for the same scan is **+7.829869%** and the AR marker cup/ball relative height difference is about **+4.23 cm over 1.108m**. All three are based on different imperfect signals; none can be presumed physical truth.
- An additional wood-colored-floor planar-homography regression with ARCore VIO priors gave forward slope **−0.80%** on all selected pairs, **+0.15%** early versus **−1.40%** late, and **−0.15%** wide-camera-baseline versus **−2.94%** shorter-baseline. Across all selected matches its **median reprojection residual was about 2.35 pixels**. These are preliminary nonproduction estimates, dependent on the selected floor mask and pose data.
- Decomposing homographies without using the ARCore inter-frame translation also gives inconsistent plane orientations; near-pure rotation and planar geometry are degenerate. It is not an independent, validated meter.

At 2m range, the idealized stereo first-order depth uncertainty for `fx ≈ 480.7`, `baseline ≈ 0.24m` is approximately **34.7mm per 1 pixel of disparity uncertainty**. A 0.5pp grade tolerance along 1m corresponds to a 5mm rise/run difference; the required consistent subpixel measurement and camera/IMU gravity constraints are demanding. These are *indicative first-order calculations*, not an observed 34.7mm RMSE or a proof of impossibility.

## Engineering status and boundary

- **PASS:** camera capture code, upload, 22 real color frames and 915 inertial samples, 24cm camera VIO baseline.
- **PASS:** some image correspondences can be metric-triangulated using ARCore camera poses.
- **NO-GO:** current v10.8 Depth-derived putting line accuracy.
- **NOT DEMONSTRATED:** repeatable physical ground grade within 0.5 percentage points with RGB reconstruction.
- **UNPROVEN:** phone hardware fundamentally incapable of sufficient precision; another phone would fix this.

The `reconstruct_rgb_plane.py` research CLI is a reproducible, privacy-preserving **diagnostic**. It flags lack of frames, bad JPEGs, inadequate camera parallax, candidate reconstruction counts and inconsistent plane estimates. It has **no certified slope accuracy**, intentionally does not drive aim guidance, and is not yet a generic grass segmentation or nonplanar green model. Synthetic CI tests cover calibrated projection/unprojection and failure handling.

### Next steps before further instrument tests

1. Compare alternative pose-adjustment and gravity constraints OFFLINE, without altering published Depth slope math, using frame subsets withheld from calibration.
2. Quantify uncertainty from image feature reprojection, camera pose, and per-scan gravity alignment. A low reprojection error alone is not sufficient.
3. Only if independent reconstructed grade passes *repeatability* with separate frame subsets, perform a short physical reference test: tape-measured approximately 1m A→B, independent spirit-level/shim rise in millimeters, same two marks, direction reversed. No extra phone purchase or general APK tuning.
4. If physically verified median grade error >0.5pp or repeat span >0.5pp remains, **do not release putting guidance**. Consider a different sensing modality or a less precise product rather than an endless camera-version churn.

Do not claim `ARCore VIO camera pose + RGB` is independent ground truth: the camera poses share a tracking stack with earlier ARCore diagnostics. An independent image-only pose estimate also has a planar homography/metric-scale ambiguity unless anchored to physical distance and gravity.


## Pose refinement / model identifiability (offline follow-on)

A separate research-only **planar bundle adjustment** fit the image correspondences across eight sampled views. It optimized one arbitrary planar floor and small camera pose corrections using a soft ARCore VIO pose prior and smoothness regularization, while withholding 1/4 of image pairs from fitting. It did **not** assume the plane is horizontal in its free-slope trial.

- Without pose refinement: held-out median image correspondence residual **3.08 pixels**.
- With free-slope planar pose refinement: held-out median **0.568 pixels**, fitted longitudinal grade **−3.24%**; maximum camera correction ~**1.09cm** translation and **0.64°** rotation.
- **Identifiability stress test**: artificially constrain the **hypothetical** longitudinal grade, independently reoptimize small camera pose corrections, and compare held-out image reprojection. These are NOT floor measurements:

| Hypothetical fixed grade | Held-out median reprojection | Max pose-angle correction | Max pose-position correction |
| --- | ---: | ---: | ---: |
| −1.5% | 0.583px | 0.37° | 1.13cm |
| 0.0% | 0.594px | 0.32° | 1.15cm |
| +1.5% | 0.642px | 0.54° | 1.21cm |
| +3.5% | 0.710px | 0.99° | 1.34cm |

**Critical observation:** The archived image sequence has enough apparent flexibility in modest camera-pose adjustments to explain grade hypotheses differing by several percentage points while leaving substantially subpixel reprojection residuals. Even *with* held-out image checks, low reprojection error does **not uniquely identify** the floor's longitudinal grade to 0.5pp. This demonstration depends on assumed regularization scale, planar geometry and feature masks; it is strong diagnostic evidence of poor identifiability under the present pose constraints, **not a mathematical impossibility proof for future sensors/algorithms**.

An independent physical gravity/pose constraint with verified uncertainty smaller than ~0.286° for a 0.5pp *tilt-only* error budget, plus independent scene geometry/scale, would be needed before another putting-grade claim. Such precision has **not** been verified from this phone's ARCore/IMU outputs. Do not impose a 0% floor prior in production to make images seem accurate: it would suppress legitimate green slopes.

**Engineering decision remains NO-GO for precise putting lines.** Retain v10.8 solely as a private RGB/IMU research recorder. Avoid additional identical uncalibrated floor scans. Further work must validate an independent metric reference, sensor, or externally surveyed trajectory before user testing.
