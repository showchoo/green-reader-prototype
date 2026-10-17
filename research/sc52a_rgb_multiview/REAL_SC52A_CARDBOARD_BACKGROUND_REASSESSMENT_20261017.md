# 2026-10-17: re-evaluation of cardboard tilt with static-background diagnostics

The user's setup used **approximately 100cm-long flexible cardboard**, raised with **approximately 4cm of stacked cardboard**, with the actual height and **effective support spacing not measured**. This supersedes the earlier nominal 2% calibration claim. **Physical ground truth is UNKNOWN** and the phone's grade error cannot be calculated from these two captures.

## Offline real-session findings (raw room maps never committed)

v11.0 Camera2 DEPTH16 user-owned sessions `Session_HW_DEPTH_20261017_232314_973.zip` and `Session_HW_DEPTH_20261017_232350_431.zip`. 11 valid depth frames per state; the same front region is used in both scans after eroding moving component boundaries and discarding transient pixels.

- Changed-component rectangle at the default 20mm shift threshold: **x328..503, y22..414**, ~55,841 connected pixels; **46,832 shared stable-depth pixels** after filtering.
- Unadjusted plane-normal angle change: **3.0908° = 5.400% unsigned grade change equivalent**. This is a moving-surface candidate, **not an independently confirmed panel**.
- To investigate camera movement, predeclare seven independent/preset spatial windows outside the moving region (some windows intentionally overlap and must not be treated as independent statistical evidence). Fit background normals in both sessions and apply the **minimum-angle rotation** aligning the second background normal to the first. This is only a testable alignment convention; rotation *around* a single background normal remains unknowable.

| Background window | Normal change across captures | Background-referenced grade change | Same-ish prior normal direction |
|---|---:|---:|---|
| right_upper_inner | 1.122° | **4.09%** | yes |
| right_upper_outer | 0.464° | **4.72%** | yes |
| right_lower_inner | 1.375° | **3.19%** | yes |
| right_lower_outer | 0.230° | **5.67%** | yes |
| right_middle | 0.504° | **4.64%** | yes |
| right_wide | 0.563° | **4.51%** | yes |
| left_bottom_control | 0.233° | 5.55% | **NO** (different plane direction ~77°) |

The six nominally similar backgrounds yield **3.19–5.67%**. The 4.09% agreement with the user's *roughly inferred* 4cm/100cm is a **coincidence until independently calibrated**, because selecting it would be post-hoc cherry-picking. Further, the background normals vary 0.2–1.4° across shots even though foreground/background distances appear mostly stable: this alone is significant relative to the target ±0.5 percentage point grade accuracy and cannot be declared real camera rotation without independent reference.

## Conditional arithmetic — not observations

- 40mm rise / 1000mm support span = 4.00% grade.
- 40mm rise / 800mm support span = 5.00% grade.
- 40mm rise / 740mm support span = 5.41% grade.
- A flexible panel's full length is **not** its effective support span, nor a measured slope reference.

## Engineering changes and go/no-go

- `compare_static_background_references.py` produces **every** preset reference estimate and explicitly retains unknown camera-normal-axis rotation, scene identity and lack of certified accuracy; no user images sent outside authorized workspace.
- Synthetic `test_compare_static_background_references.py` ensures that known camera-frame rotation can be corrected *under its assumptions* and that rotation around the reference plane's normal **cannot** be corrected from that normal alone.
- `physical_grade_reference_gate.py` refuses missing/unmeasured rise, run, rigid plane or initial horizontal verification. It conservatively propagates the provided physical ruler tolerances, imposing at most ±0.15 percentage points on the external reference before any 0.5pp phone test.
- `test_physical_grade_reference_gate.py` validates the refusal, invalid bounds and propagation. GitHub Actions runs these tests and existing axial-vs-radial synthetic geometry checks.

A reference measurement of e.g. **16.0mm true rise over 800mm true support spacing** on an independently level-verified rigid board, actual uncertainty ±1mm rise and ±5mm span, would give a 2% grade reference with about ±0.14 percentage points worst-case reference uncertainty. Such a test has **not** yet been performed; do not infer it from cardboard.

**Current disposition:** v11.0 unchanged; Camera2 raw acquisition and internal normal repeatability are promising; physical putting-grade accuracy **INCONCLUSIVE**. Do not ship depth-derived commercial putting-line guidance or encourage new phone purchases. Any further physical test should use a rigid target, marked supports, measured rise/run and unchanged mount; no blind repeated cardboard trials.
