# v11.3 fixed-mount before/after depth-only experiment (private offline)

**No app update required.** Use v11.3 with the Record button visible.

### Physical setup

The data recorded at 04:23:21 with the raised level board is the
**board-present** candidate. It cannot be compared to the older captures:
their camera orientation changed markedly.

For a valid next pair, the phone and mount must not be shifted, tilted, or
rotated between captures. Without a surveyed absolute pose, IMU direction
agreement cannot detect pure translation or yaw. An independently rigid
mount is mandatory. This test measures *relative optical-axis depth
differences*, not physically certified 50mm board height or golf grade.

If the mount has NOT been moved since the 04:23:21 capture, carefully remove
the entire board and its supports WITHOUT TOUCHING the phone or mount, and
capture the empty floor with v11.3 once. Name it as the --empty input, and
use the 04:23:21 ZIP as --board.

If the camera was moved, the earlier capture is **not** an eligible board
reference. Perform two fresh captures with one fixed mount in the order:
empty floor, then put the supported level board in place without touching
the phone, and capture board-present. Both captures must visibly include
unchanged floor around the board.

For both cases, ensure the DEPTH16 live preview shows a sizable floor
background, a central raised region and no strongly changing external
objects. The colored contour alone does not prove the board's identity.

### Offline command

python3 research/sc52a_rgb_multiview/audit_paired_elevated_board.py \
  --empty "/private/empty-floor.zip" \
  --board "/private/raised-board.zip" \
  --output "/private/research-only-paired-report.json"

Reports remain private; never commit ZIP files. The code rejects missing
matched pixels, different camera calibration, incompatible timestamp sources,
large IMU direction changes, globally shifted range, camera-edge changes
and too many unrelated depth candidates. A candidate status is never board
identification: per-ray depth changes may also come from camera translation
or movement of other objects.

Observed vendor DEPTH16 confidence code is very low in all existing S20+
captures. A successful synthetic test or 50mm-like real image difference
does not certify height / slope measurement accuracy.
