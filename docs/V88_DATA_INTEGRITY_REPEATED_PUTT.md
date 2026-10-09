# v8.8 — Metadata integrity and repeated-putt research

## Why this release exists

The 83 historical arrows We2 M07 field scan packages contain:
- 52 golf-course scans recorded by **Precision 7.1**; all 52
  `metadata.json` files contain escaped quote delimiters that render
  the raw JSON invalid. The generating bug was repaired in the v7.3
  source patch. v8.8 adds a regression that explicitly parses the
  generated JSON templates after ALL cumulative patches are applied.
- 31 later home scans from **Precision 7.5**; their metadata JSON is
  valid.
- **No putt has 2 or more successful scans** within its recorded
  `session_id`, `hole_number` and `putt_id` group. Some putts have
  several scans, but failed scans cannot establish repeatability.

The earlier 8→19 internal flank-direction agreements in 83 offline scans
are **not** proof of measured hook/slice accuracy. Without same-putt
successful repeats and known physical ground truth, repeatability cannot
be calculated reliably for the old dataset.

## App change (v8.8, versionCode 880)

Generated `ScanFieldRecorder.escape` now encodes all ASCII control
characters in dynamic JSON strings (including backspace, form feed,
carriage return, tab and other U+0000..U+001F characters), in addition to
JSON backslashes, quotation marks and newlines.

This is solely a saved-file integrity fix; it does **not** modify:
- any slope, distance, or line calculation
- v8.2 flank-distance alignment and v8.4 matched flanks
- v8.3 multi-radius direction-consistency rejection
- v8.5–8.7 frame pose, pixel ray and temporal diagnostics
- putt foldering, photos, optional result input or signing compatibility.

Post-generation tests parse the synthetic `metadataJson`,
`failureMetadataJson`, `recordIdentityJson` and `qualityJson`
templates as JSON, preventing regressions back to the v7.1 quote
problem.

## Offline repeatability report

Run on a desktop with Python 3.9+:

```sh
python3 scripts/analyze_precision_session_consistency.py \
    SessionA.zip SessionB.zip \
    --scan-csv scans.csv \
    --putt-csv putts.csv
```

This tool only reads `record_identity.json`, `metadata.json`,
`scan_quality.json` and `collector_diagnostics.txt` from each
scan folder. It deliberately does **not** open `camera.jpg` or read
the large Depth point cloud.

It produces **two CSV summaries**, preserving failures:
- `scans.csv`: outcome, app version, metadata validity, reported
  long/cross grade, distance, quality, Raw/Full accepted-frame counts,
  number of camera telemetry blocks and optional pose-history samples.
- `putts.csv`: per-putt success/failure counts, comparable successful
  repeats, difference ranges, possible strong sign contradictions and
  reasons that a comparison is invalid.

For comparisons the tool requires:
1. at least two successful reported slopes within the *same putt*
2. the same approximate measured putt distance (within max(20cm,15%))
3. ball→cup world horizontal headings within 15°, within that AR session

If these conditions fail it records an explicit inconclusive status,
rather than declaring a contradiction.

Even within the limits a disagreement can result from real nearby
contours, variable ball/cup placement, AR tracking drift, or sensor
bias. These checks are **research flags**. Consistency is not accuracy.

Legacy v7.1 invalid JSON is *recognized only for that known app version*
and decoded on a best-effort basis, labelled
`legacy_recovered_untrusted`. The original files are untouched;
recovered dynamic text is **not** proof of file authenticity or perfect
recovery. Unknown invalid JSON is rejected without guessing.

## Suggested M07 field test

Use v8.8 on a stationary, reasonably even surface. Complete one
three-scan group **without pressing 次のパット between attempts**:

1. Mark the **same** ball and cup positions and keep them unchanged.
2. Record scan 1 slowly from the middle view.
3. Reset only the scanning process, not the putt group, and repeat
   scan 2 with a small lateral view change.
4. Repeat scan 3. If any scan fails, keep collecting until there are
   at least three *successful* scans in that putt group.
5. For the *next* independent setup, use 次のパット before moving markers.
6. Export the entire session ZIP (keeping per-scan folders intact).

For device-dependent bias calibration, measure the true left/right
height difference with an independent level or inclinometer, and record
left/right reference distances separately. A home floor alone is
not guaranteed level.

A practical initial goal is **3 successful scans of the same putt**
at each of several fixed locations, and the same arrangement from
different viewing directions. Do not substitute failed scan counts
for successful repeats.

## Privacy and scope

Session ZIPs may contain private photos or location-sensitive data.
No real field ZIP, camera image, depth cloud, or result file was pushed
to the public GitHub repository.

Do not merge this into `main` until Android build and prior-key APK
signing checks pass. Android CI passes do not imply verified physical
measurement accuracy.
