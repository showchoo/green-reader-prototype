# 2026-10-18 — confirmed A=level, B=raised, C=level, D=raised (SC-52A)

## User-confirmed condition order

The user explicitly confirmed, after four signed v11.0 Camera2 DEPTH16 archives arrived, that the captures were **level → raised → level → raised**. This supersedes *condition-order ambiguity* from the prior four-session report and PR #62. The 2% reference magnitude is still **NOT independently verified** by measured 16mm rise over 800mm between physical supports, actual target rigidity, surface pixels, or unchanged camera mount.

| Condition | Japan local timestamp | User-owned Drive ZIP suffix | Nonzero depth frames |
|---|---|---|---:|
| A level | 2026-10-18 00:20:38 | 002038_623 | 11 of 12 |
| B raised | 2026-10-18 00:21:08 | 002108_029 | 11 of 12 |
| C level | 2026-10-18 00:23:28 | 002328_291 | 11 of 12 |
| D raised | 2026-10-18 00:23:54 | 002354_752 | 11 of 12 |

Each capture: Camera2 ID4 640x480; reported zero hardware capture errors; median valid pixel coverage 88.36, 88.93, 88.71 and 88.69% respectively. No raw room images or point clouds in the public repo.

## Four pair types

The correct *two experiments* are **A→B** and **C→D**. **A↔C** are two nominally level scenes; **B↔D** are two nominally raised scenes. Comparing A→C or B→D as if they are level→raised is a **category error**. Previous claims of 1.9% in a right-hand region for A→C do NOT show the app detected a true 2% tilt. In the same ROI, A→B and C→D show almost no change.

Nominal device gravity-direction differences (from averaged/matched Android gravity, alternative sampling gives ±0.01°):

- A→B: **~0.02–0.03°**; C→D: **~0.03°**.
- A↔C: **~1.23°**; B↔D: **~1.24°**.
- Gravity direction is only a sensor-frame proxy; it does NOT verify an unchanged position, yaw angle or depth-sensor extrinsic orientation.

## Same predeclared optical-axis depth plane model, all relevant regions

The numbers below are **unsigned camera-frame plane-normal rotations converted using 100*tan(angle)**, not physically verified floor or putting grade. Robust 3D plane fits use the sensor's camera intrinsics and distortion. Regions can mix the physical board, walls or floor.

| Fixed image ROI | A→B (% equivalent) | C→D (% equivalent) | A↔C (both reported level) | B↔D (both reported raised) |
|---|---:|---:|---:|---:|
| Whole inner image | **0.63** | **0.84** | 1.33 | 1.86 |
| Left | **0.81** | **1.20** | 1.76 | 2.97 |
| Center | **1.37** | **0.83** | 0.96 | 1.29 |
| Right | **0.02** | **0.06** | 1.91 | 1.88 |
| Center-lower | **1.86** | **1.26** | 1.31 | 1.68 |
| Far right | **0.29** | **0.03** | 1.70 | 1.72 |

The physical target might be in the left or center while the far right is static background, but its location is **not verified**: this depth-exclusive Camera2 research path has no registered color camera preview or fiducial detection. Crucially, **no predeclared ROI consistently recovers a calibrated 2% change in both A→B and C→D**. The apparent right-hand ~1.9% was instead recorded between **two nominally level scenes** with 1.23° device posture difference and is not positive proof of target slope detection.

## Repeated signal / spatial segmentation experiments

The *orientation of the normal-change vector* within the fixed central ROI was consistent for both level→raised pairs: cosine about **0.992** in camera coordinates; fixed center-lower cosine about **0.991**. This suggests a repeatable response to the physical intervention, but the **magnitude** differs substantially between the two experiments and no independent board label exists.

A non-cherry-picked research alternative created a mask from the largest connected image region that **became nearer by >=5mm** in the *first* pair, excluding a 15px border, and applied this mask unchanged to the second independent pair. This yielded unsigned camera-frame normal grade equivalents of approximately **0.61% (train A→B) and 1.18% (holdout C→D)**. Reversing mask discovery (**C→D**) yielded about **1.28% (train C→D) and 1.14% (holdout A→B)**. Both estimates remain away from a presumed 2% and depend on which moving region is selected. At lower/higher movement thresholds the results change. Some auto-identified moving regions give **opposing normal-change vector directions** across the two pairs, unlike the fixed central ROI: **no validated automatic board segmentation**.

The signed or absolute grade cannot be certified from an arbitrary normal-change magnitude in the wrong ROI. Same-condition A↔C also differs due to device orientation; do not treat these as repeated same-pose captures.

## Disposition

1. **PASS**: four correctly classified scans with real metric DEPTH16 data, two independent level→raised interventions, low per-pair device roll/pitch drift and some repeatable directional response.
2. **FAIL TO CERTIFY / INCONCLUSIVE**: physically measured 2% grade tolerance ±0.5 percentage points. Neither support spacing nor actual shim elevation was confirmed in this dialog for these specific sessions, and the board pixels are not independently identified. Avoid declaring direct Camera2 phone accuracy from ROI values alone.
3. **NEXT TECHNICAL BOTTLENECK**: obtain a verified board/target mask in the Camera2 depth image (e.g. depth-only visual preview/fiducial geometry, or a consistent physically known panel region), plus an independently measured rigid plane support span and lift, without camera posture/position changes between all four conditions. No more unstructured repeated recordings and no new APK until the exact evidence gap is specified.
4. Keep user room ZIPs and private depth maps **outside public GitHub**. Use aggregated public reporting and synthetic tests only.

The companion `score_confirmed_alternating_pairs.py` accepts explicitly ordered A/B/C/D private ZIPs, reports all predefined ROIs, both intervention pairs, same-condition comparisons, gravity motion and optional camera-frame directional cosine. It never claims commercial slope accuracy.
