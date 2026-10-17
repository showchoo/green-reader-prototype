# 2026-10-17 SC-52A DEPTH16: optical-axis vs Euclidean-range geometry

## Motivation and critical correction

A prior exploratory fit interpreted each Camera2 DEPTH16 low-13-bit value as a **Euclidean radial distance** and projected it onto a unit ray. Android `ImageFormat.DEPTH16` guarantees a millimetre **range measurement**, but does not by itself settle the interpretation of every vendor's optical-axis geometry. We therefore tested two explicit hypotheses on **both** real S20+ session archives without assuming a surveyed floor angle:

- **Optical-axis Z hypothesis:** 3D point `[u',v',1] * depth_mm/1000`, where `(u',v')` are lens-distortion-corrected normalized image coordinates.
- **Euclidean radial hypothesis:** 3D point `normalize([u',v',1]) * depth_mm/1000`.

Camera2 `LENS_DISTORTION` is `[k1,k2,k3,p1,p2]`; OpenCV requires `[k1,k2,p1,p2,k3]`. Both alternatives use the exact same camera intrinsics and distortion-corrected pixel rays.

The test region is **x=350..620, y=80..400** in a 640×480 DEPTH16 image. It was selected as a geometrically coherent right-side region during examination of the fixed capture; **it was not independently identified as floor**. The study uses two held-out spatial tests per frame:

1. Fit a robust plane on upper/right region y80..240, evaluate orthogonal point-to-plane residual on lower/right region y240..400.
2. Fit on inner/right region x350..480, evaluate on far-right region x480..620.

Training/testing locations are disjoint within each frame. The measurements below summarize medians over each session's eleven nonempty frames; they are **mm deviations from an estimated plane**, *not* surveyed height errors.

| Session | Held-out slice | Optical-axis hypothesis median residual | Radial hypothesis median residual | Radial/axial ratio |
| --- | --- | ---: | ---: | ---: |
| Hand-held `Session_HW_DEPTH_20261017_222431_073.zip` | upper → lower | **1.956mm** | 20.031mm | 10.24× |
| Hand-held | inner → outer | **2.528mm** | 18.686mm | 7.39× |
| Fixed `Session_HW_DEPTH_20261017_224806_554.zip` | upper → lower | **4.324mm** | 29.990mm | 6.94× |
| Fixed | inner → outer | **3.555mm** | 24.460mm | 6.88× |

Fixed-session optical-axis held-out p90 residuals were 8.735 and 7.233mm; hand-held were 4.540 and 5.193mm. These residuals depend on which actual surfaces the patches contain. Small plane residuals do not establish small systematic errors; a biased planar surface can fit very well.

**Most important engineering finding:** On both archived real scenes, and independently held-out image regions, the data's planar consistency is **about 7–10× better under the optical-axis/Z hypothesis**. Therefore the earlier radial-projection evaluation **must not be used to reject the direct Camera2 depth modality or assess physical grade accuracy**. This is a much more plausible geometry model for this SC-52A scene, but a vendor API contract or independent physical depth calibration is still needed before declaring true semantics.

Previous observations (code-2 low confidence everywhere, central distance median stable but pixel changes, lack of externally measured rise/run) remain relevant. Neither hypothesis has a physical ground-truth certification.

## Reproducibility and CI

- `compare_depth_geometry_models.py`: calibration handling, two explicit 3D hypotheses, robust geometric plane fit and spatial holdout, summary-only output.
- `test_compare_depth_geometry_models.py`: synthetic true-Z and true-radial planar scenes; verifies that the correct model wins in each case, not simply a built-in Z bias. Invalid calibration/zero depth fail closed.
- `evaluate_measured_incline_pair.py`: accepts **two independent captures of one identical planar target** with the device fully fixed; first physically level, then a known rise in mm over a measured run in mm. Reports the *unsigned* change in plane-normal orientation and the independent physical reference. It **does not** infer signed slope, physically verify device immobility, or certify commercial accuracy.
- `test_evaluate_measured_incline_pair.py`: 20mm/1000mm simulated known tilt, mandatory nonzero run and invalid negative shim.
- Separate GitHub Actions synthetic tests; no user photos, depth images or raw ZIPs checked in.

## Next physical gate

The only defensible next test after code review is to keep the SAME fixed Camera2 ID 4 (v11.0) phone view, place an **identifiable flat board/rig** that fills the intended capture region, and obtain two independent user-confirmed conditions:

1. Board level measured with a physical spirit level; direct DEPTH16 v11.0 capture, keep camera fixed.
2. Without moving phone or altering board material/position except its planned tilt, raise **one end by measured 20mm over a measured 1000mm baseline** (2.0% grade); second v11.0 capture.

The existing app has no RGB preview for this exclusive depth camera, so if the board does not fill an identifiable common region, the data may be unusable: do not force a plausible result from another object. The analysis must evaluate identical ROI and external rise/run and insist that both sessions have enough points/stable within-session normals. A single board pair *only tests change in inclination* and does not prove the worst-case or commercial suitability. Further reference cases (e.g. negative tilt, different board texture, true golf green) would be needed before release.

Success criterion for a **preliminary R&D GO**, not a product PASS: actual measured grade change agrees with independent 2% angle within 0.5 percentage points, while within-capture normal drift stays well below 0.286°. Failure or absent usable planar area means **NO-GO until an actual calibration/segmentation mechanism**. Do not create more blind Depth APK builds. Keep existing v11.0 researcher, without putting guidance certification.

## Core caution

`LENS_POSE_REFERENCE_PRIMARY_CAMERA` is reported by the SC-52A capture; one must not equate its orientation directly with the Android gravity vector without proving the sensor/primary-camera coordinate transform. By comparing changes between two views recorded from one mechanically fixed device, the preliminary board experiment minimizes reliance on an unverified **absolute** camera-to-gravity rotation. The experiment does not remove lens or depth systematic calibration errors or prove the phone never moved.

Authoritative Camera2 field documentation:
- https://developer.android.com/reference/android/graphics/ImageFormat
- https://developer.android.com/reference/android/hardware/camera2/CameraCharacteristics


## Temporal early/late holdout in the identical ROI

Using only the optical-axis interpretation and the same preselected x350..620, y80..400 region, compare robust plane normals from frames 1–5 and 6–11 of the *11 nonempty frames*. These two portions have no overlapping timestamps:

| User session | Angle between early/late median normals | Hypothetical unsigned grade change `100*tan(angle)` |
| --- | ---: | ---: |
| Hand-held, 22:24 | **0.39752°** | **0.6938%** |
| Mechanically fixed, 22:48 | **0.00429°** | **0.0075%** |

Across all fixed frames in this selected ROI, the largest departure of a single-frame normal from the session median is about **0.0283°**. For hand-held frames it is about **0.4937°**. Fixed-session orthogonal plane-fit p50/p90 residuals within that ROI are approximately **2.91/6.51mm**.

These are **repeatability diagnostics in a particular candidate planar region under one unchanged setup**, not a physical ground-truth grade error, nor evidence of green-surface accuracy. Device stillness, scene selection, lens model bias, and sensor code-2 confidence remain limiting. Their value is that the acquisition has sufficient *internal angular stability* to justify one measured relative-incline experiment without another APK.
