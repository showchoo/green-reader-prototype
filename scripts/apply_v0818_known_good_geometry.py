from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.18 pattern not found ({label}):\n{old[:1800]}")
    s = s.replace(old, new, 1)

# Start from the field-confirmed v0.8.7 geometry/overlay path. The only tap change is:
# never keep a failed screen coordinate alive. A failed acquisition leaves markMode on
# the same target so the user simply taps again. This removes the sticky-failure state
# without changing the 3D point / Anchor convention that produced the correct arrow in
# v0.8.7.
old_mark = '''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return
        val f = latestFrame
        if (f == null) {
            status.text = "ARの準備中です。端末を少し動かしてください"
            return
        }

        val p = resolveMarkPoint(f, x, y)
        if (p != null) {
            applyMark(mode, p)
            return
        }

        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime())
        markMode = 0
        status.text = "位置を取得中… そのまま端末を少しだけ動かしてください"
    }
'''
new_mark = '''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return
        val f = latestFrame
        if (f == null || f.camera.trackingState != TrackingState.TRACKING) {
            status.text = "ARの準備中です。端末を少し動かしてからもう一度タップしてください"
            return
        }

        val p = try {
            resolveMarkPoint(f, x, y)
        } catch (_: Throwable) {
            null
        }
        if (p != null) {
            applyMark(mode, p)
            return
        }

        // Important: no pending retry, no reuse of this x/y on a later AR frame.
        // Keep the current target active and ask for one fresh tap.
        pendingMark = null
        markMode = mode
        status.text = if (mode == 1) {
            "ボール位置を取得できませんでした。もう一度タップしてください"
        } else {
            "カップ位置を取得できませんでした。もう一度タップしてください"
        }
    }
'''
replace_once(old_mark, new_mark, "single-shot v0.8.7 marking")

# The old pending resolver is now unreachable by touch input. Remove the render-loop
# call as well so a stale PendingMark can never alter state after reset.
old_retry_call = '''            if (f.camera.trackingState == TrackingState.TRACKING) {
                tryResolvePendingMark(f)
            }

'''
new_retry_call = '''            // Failed marks are single-shot. Never resolve an old screen x/y on a
            // later camera frame; the user supplies a fresh tap instead.

'''
replace_once(old_retry_call, new_retry_call, "remove delayed mark retry")

# Reset invalidates all mark state and immediately returns to Ball marking.
reset_start = s.find("    private fun resetAll() {")
reset_end = s.find("    private fun showMap()", reset_start)
if reset_start < 0 or reset_end < 0:
    raise SystemExit("v0.8.18 resetAll boundaries not found")
reset = s[reset_start:reset_end]
if "pendingMark = null" not in reset:
    raise SystemExit("v0.8.18 reset does not clear pending mark")
# v0.8.2 auto-sequence should already restore markMode=1; assert rather than invent.
if "markMode = 1" not in reset:
    raise SystemExit("v0.8.18 reset does not restore Ball mark mode")

# v0.8.12 consensus is applied before this patch in CI. Tighten the final direction
# decision from 3/5 to 4/5 while keeping median magnitudes.
old_consensus = "        val combined = SlopeConsensus.combine(consensusReports)\n"
new_consensus = "        val combined = SlopeConsensus.combine(consensusReports, minAgree = 4)\n"
replace_once(old_consensus, new_consensus, "4-of-5 consensus")

# Keep effectively-flat arrows suppressed. No later display-side sign calibration is
# applied in this build; v0.8.7's Anchor-local projection remains the sole direction
# mapping.
if 'appVersion = "0.8.12"' in s:
    s = s.replace('appVersion = "0.8.12"', 'appVersion = "0.8.18"', 1)
elif 'appVersion = "0.8.0"' in s:
    s = s.replace('appVersion = "0.8.0"', 'appVersion = "0.8.18"', 1)
else:
    raise SystemExit("v0.8.18 appVersion target not found")

if "tryResolvePendingMark(f)" in s:
    raise SystemExit("v0.8.18 delayed mark retry remains active")
if "SlopeConsensus.combine(consensusReports, minAgree = 4)" not in s:
    raise SystemExit("v0.8.18 strong consensus missing")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.18 known-good v0.8.7 geometry + single-shot taps + 4/5 consensus")
