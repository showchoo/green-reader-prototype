# Green Reader Precision v10.0 — M07 sparse Raw Depth acquisition correction

## Scope and limits
v10.0 is an acquisition/evidence update built *after* v9.9 using scripts/build_precision_v100.py; it does **not** calibrate the floor or prove slope accuracy. The ball-anchored ground selector, ground-cell acceptance rules, marker/Depth height cross-check, line suppression and Drive save/backup remain in place.

### Observed 2026-10-10 captured data
All counts below were computed from the saved precision_depth_sources.csv frame timestamps, not estimated from UI percentages.

- v9.8 healthy Raw-only scans (sampled six): each frame had approximately 384–453 accepted points. One 99-frame scan median = 439/frame.
- v9.9 failed Raw-only scans: 8–25 accepted points/frame (four sampled scans), generally 14–16 median.
- v9.9 7:45 failed scans: approximately 64–103 accepted points/frame (three sampled scans), medians approximately 80–82.
- v9.9 successes happened to have Full Depth at approximately 873–920 points/frame, but both failed marker-vs-Depth agreement checks by ~8.4 cm. Full is **not** an absolute accuracy oracle.

### Why this change
The previous Full Depth supplement policy treated *any* successful Raw pixel as adequate for short putts. A Raw frame contributing only 8–103 points could therefore suppress Full Depth entirely, even if the reconstructed ball-to-cup surface was unobservable.

v10.0 sets an empirically motivated acquisition threshold of 160 accepted Raw points per frame. Raw below this threshold supplements from Full across the requested depth range; healthy dense short-range Raw stays Raw-only. The existing long-range Full supplement rule is preserved.

- Per-window logs include sparseRawFrames, sparseRawFullAcquired, rawAcceptedPointTotal and lastRawPoints.
- The old per-depth-source CSV, camera frames and scan failure records remain.
- If the aggregate is Full-dominated while repeated Raw remains sparse and the two sources have **not** independently agreed, suppress **directional guidance** and high-quality marking; do not silently certify the estimate.
- Do not lower floor-selection candidate counts, lower temporal support, force a horizontal result, or replace the selected floor with a global-height histogram.

### Safety and verification
The new per-frame acquisition threshold is *not a calibrated slope error bound*. Unit tests check 0/1/8/14/16/80/103/159 Raw points require Full; 160/384/399/439/453 do not for a short putt. A synthetic sparse/mixed-source scenario must suppress directional advice until source agreement; healthy Raw does not trigger the veto.

Next M07 test: same unchanged ball/cup placement, 3 consecutive scans, preferably an independently checked level floor. Review actual valid Raw points/frame; attempted vs actually acquired Full; ANCHORED_GROUND status; marker-height mismatch; RMSE and slope value. Do not claim an accuracy improvement until known-slope reference measurements validate it.

ZIP inputs used for diagnosis:
- Session_20261010_071422_5170b51f.zip (v9.8)
- Session_20261010_074403_e313b0cc.zip (v9.9)
- Session_20261010_074546_c6dd5ce6.zip (v9.9)
