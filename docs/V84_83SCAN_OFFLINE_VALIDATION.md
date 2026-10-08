# Green Reader Precision v8.4 — 83-scan offline check

Date: 2026-10-09 (JST). Device: arrows We2 M07.
Input: 52 golf / 17 home / 14 measured-distance historical scan packages.
Analysis: reconstruct turf cells from saved point clouds with the previous
Python surface method, then replay v8.2 median-flank and v8.4 1:1 matched-cell
flank comparisons. The result is **research-only** and is not device truth.

## Headline

| Result across all 83 scans | v8.2 | v8.4 |
|---|---:|---:|
| Directional turf-height evidence agrees with reported sign | 8 | 19 |
| Opposite sign: conservative direction veto | 1 | 1 |
| Mixed or weak slice evidence | 6 | 18 |
| Insufficient forward-aligned coverage | 25 | 2 |
| No cross direction to audit / failed scan | 43 | 43 |

There are 45 scans with a saved cross-slope result; only 40 exceed the
1.2-percentage-point flank-audit threshold. Relative to v8.2, v8.4
increased valid paired-slice coverage on 36 scans, left it unchanged
on 47, and reduced it on none.

**Important:** One previous v8.2 agreeing scan becomes mixed/weak in v8.4,
as the actual matched cell-pairs reveal additional differing local slopes.
Do not claim monotonic increase in individual "confirmed" cases.

Among the 45 scans with a reported cross slope, the v8.4
agree/veto counts by putt distance were:
- 0.4–2 m: 5 agree / 1 veto, 15 scans;
- 2–4 m: 7 agree / 0 veto, 10 scans;
- 4–6 m: 6 agree / 0 veto, 13 scans;
- >=6 m: 1 agree / 0 veto, 7 scans.

The known home-distance Putt_002 conflict persists: approximately
-2.57% reported versus +2.12% matched flank median. The earlier
+2.40% estimate came from v8.2. In v8.4, 6 of 8 valid slices
oppose the reported sign. This remains a **disagreement**, not an
independent measurement of the true green slope.

## Interaction with v8.3 multi-radius guard

Re-using the stored 32/50/80cm-radius research summary:
- Three historic scans show strong credible sign conflicts across scales.
- Zero of these three are marked agreeing by the new v8.4 flank check.
- The one scan vetoed by the flank check is among those three.
- All 19 v8.4 flank-agreeing scans also had strong same-sign 50cm and
  80cm results in the research replay.

These checks share the same depth cloud and surface reconstruction.
They are **correlated checks**, not three independent measurements.

## Risks and next implementation targets

1. This replays historical points through a Python reconstruction and is
   **not** a replay of full on-device temporal consensus/AR tracking.
2. Historical data do not include per-frame camera pose, which limits
   investigation of spatial Depth bow and view-dependent slope bias.
3. Ground truth is missing, so hook/slice correctness and absolute slope
   errors cannot be inferred from the 19 agreements.
4. Preserve fail-closed behavior for strong cross-sign conflicts; do not
   force cross-axis inversion or blanket distance calibration.
5. Next: record per-frame camera poses associated with depth timestamps
   at low overhead, then analyze viewing-angle/distance dependency using
   future automatically recorded scans.
6. Keep Android unit tests, scan auto-save, per-putt grouping, result input,
   quality logs, and signing compatibility as non-regression requirements.

## Offline reproduction

The research script accepts the 3 saved Session ZIPs, uses NumPy/Pandas
to reconstruct stable 5cm voxels and the nearby connected turf surface,
then compares grouped flank medians with distinct forward-matched cell pairs.
Never check in raw depth ZIPs or camera images to this public repository.

This report is **not** a declaration of v8.4 field accuracy. A calibrated
right/left slope reference and device field results are still necessary.
