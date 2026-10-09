# v9.9 — Anchored ground selection from M07 field evidence

## Observed failure

Earlier releases chose the height reference using the largest stable-height
bin in the whole camera view. That bin can represent interpolated furniture,
walls, or background rather than turf next to the user's marked ball.

Examples from the private M07 session recorded on October 10, 2026:

- Putt 002 Scan 02: chosen height **+0.757 m** relative to the marked ball.
- Putt 002 Scan 03: chosen height **+0.770 m** relative to the marked ball.
- Putt 002 Scan 01: chosen height **+1.218 m** relative to the marked ball.

These did not produce trustworthy ground measurements. Do **not** add these
source ZIPs or the user's camera pictures to the public repository.

## Selection change

v9.9 replaces the global height histogram with a spatially anchored selector.

1. Keep existing per-voxel multi-frame median and temporal MAD filters.
2. Require >=12 stable cells within 35cm of the actual ball marker (or >=18
   within 55cm) and with height no more than ±20cm from its AR position.
3. Select a robust local height layer instead of the most populous bin in
   the entire camera scene.
4. Seed the connected-ground flood-fill only from these supported local
   ground cells. A globally abundant distant layer cannot start the region.
5. When local evidence is absent, return an empty surface and keep the scan
   failed. Do not invent or flatten the slope.

The selector's status, support counts, radius and reference height are logged
as ANCHORED_GROUND in the existing precision diagnostics and backed up to Drive.

## Evidence before field testing

A preliminary offline point-cloud count over the two private v9.8 sessions
started at 07:12 and 07:14 found eligible near-ball candidates in all 10 scans.
Two earlier Putt-002 failures with globally selected surfaces 0.757m and 0.770m
above the ball would be rejected by the same eligibility test.

This check is a **reference eligibility test**, not a byte-identical replay of
all Kotlin computations, and not a confirmation of real-world slope accuracy.

Unit tests cover:
- Dominant furniture layer cannot override nearby floor.
- No anchored ground => no surface => no false result.
- Real sloped green remains sloped, not forced horizontal.
- A position/height offset around the ball anchor is supported.
- Sparse anchors and severe height mismatch fail closed.

The existing v9.8 Depth-session restart, multi-scan workflow, original scan
point archiving, and Google Drive automatic ZIP syncing remain unchanged.

## Acceptance and next test

Upgrade M07 from v9.8 to v9.9. At a verified level surface, record three
scans for one pair of ball/cup marks. Record whether every scan is accepted and
the measured longitudinal/cross slopes. Then use a *known* inclined plane for
ground truth. Scores and inter-scan agreement are not substitutes for accuracy.

Do not market v9.9 as high precision before physically verified ground truth.
