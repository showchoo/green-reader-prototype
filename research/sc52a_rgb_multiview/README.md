# Green Reader: RGB multiview redesign feasibility (2026-10-16)

**Status: RESEARCH ONLY. Do not ship v10.7, relax the unsafe aim-line gate, or infer precise slope from current S20+ ARCore Depth.**

## Evidence from user-confirmed spirit-level indoor floor

On saved session `Session_20261016_024205_8c44c70d.zip`, five Putt_002 numerical scans of the same approximately 0.957m physical baseline gave production forward grade **-2.11%, +1.99%, +1.48%, +2.08%, +4.02%** (spread **6.13 percentage points**). No exact surveyed millimeter rise was recorded.

An offline alternative decomposed each timestamp's Raw Depth cloud into independently fitted planes, allowed **a free vertical offset for every frame**, and checked agreement across time and between independent spatial subsets. Results:

| Scan | Raw-frame median forward grade | Raw-frame median cross grade | Frame-forward spread | Frame agreement |
| --- | ---: | ---: | ---: | --- |
| P002 S01 | +0.005% | -4.421% | 3.921pp | REJECT |
| P002 S02 | +2.470% | -4.149% | 2.183pp | REJECT |
| P002 S03 | +1.391% | -2.656% | 3.022pp | REJECT |
| P002 S04 | +3.661% | -4.123% | 0.764pp | REJECT |
| P002 S05 | +3.550% | -2.342% | 5.594pp | REJECT |

Another v10.6 indoor session yielded six numerical scans, **all six also rejected** by this conservative experimental gate. This is useful for fail-closed detection but **does not recover accurate grade**. On curving greens, some planar gates could be overly strict; they are not a production algorithm.

## Independent RGB signal

Five archived normal camera JPEGs in the later session support SIFT and geometrically verified **2D image matching** across four consecutive pairs:

| Pair | RANSAC planar-homography inliers | Image-grid cells covered |
| --- | ---: | ---: |
| 01->02 | 81 | 10 |
| 02->03 | 114 | 9 |
| 03->04 | 428 | 16 |
| 04->05 | 186 | 16 |

An earlier v10.6 session yielded another 126 and 210 pairwise inliers. Matches show trackable indoor texture; they **do not** show reliable metric depth, camera translation baseline or measured 3D slope. A 2D homography explains a single plane without yielding the required vertical profile. Saved sessions have only a still JPEG per scan, not continuously synchronized RGB frames and independently calibrated IMU data, so old logs **cannot** validate stereo reconstruction.

## Engineering decision

**Do not make another ARCore Depth correction APK.** A different source of 3D geometry must be demonstrated before renewed field testing.

Authorized next *research* path:
1. Independently synchronized 10-30fps RGB tracks, camera intrinsics/distortion/crop, exposure and timestamps; gravity/IMU and camera pose only as a comparison channel (not assumed ground truth).
2. Robust feature tracks on green texture with foreground/moving-object masks.
3. Multi-view pose estimation and bundle adjustment; reject near-pure-rotation and planar-homography degeneracy instead of reporting 3D where none can be identified.
4. Fix metric scale with a known physical baseline/object; independently verify gravity alignment. Depth can be compared as an **uncertified** auxiliary signal.
5. Reconstruct held-out ground heights, not merely an image mosaic. Cross-validate different viewing subsets at flat and measured 1-3% slopes. Do not force any surface grade to 0.
6. Engineering go/no-go target: median physical grade error <=0.5pp, worst <=1.0pp, repeated grade spread <=0.5pp. On a 1m line, 0.5pp means approximately **5mm height difference**. If independently reconstructed heights cannot reach this, stop the phone-only noncontact precision approach; external measured reference/sensor may be necessary.

**Current state:** ARCore-only precision pipeline **NO-GO**; frame-slope consensus **NO-GO** as a fix; RGB 2D tracking **FEASIBLE** indoors; RGB metric 3D + sub-percent grade **NOT YET ESTABLISHED**; inability of the S20+ hardware itself **NOT PROVEN**.

Do not commit raw user session ZIPs or room photos to this repository. Only aggregate feasibility results and synthetic-code tests should be checked in.

ARCore documentation: https://developers.google.com/ar/reference/java/com/google/ar/core/Frame and https://developers.google.com/ar/develop/java/depth/raw-depth?hl=ja
