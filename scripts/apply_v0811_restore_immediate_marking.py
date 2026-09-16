from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.11 pattern not found ({label}):\n{old[:1600]}")
    s = s.replace(old, new, 1)


# v0.8.7 was field-confirmed to display the downhill direction correctly. The
# cross-axis projection code from that build is still present; the regression began
# only after v0.8.9/v0.8.10 changed how tap coordinates were resolved. Restore the
# successful v0.8.7 behavior: resolve the tap immediately against the frame currently
# shown to the user. Unlike the old implementation, do NOT keep a failed tap pending
# and do NOT retry the same x/y on later frames. A failure simply leaves markMode
# unchanged so the user can tap again. This removes the sticky-failure state entirely.
old_mark_at = '''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return

        val token = markAttemptToken + 1L
        markAttemptToken = token
        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime(), token)
        markMode = 0
        status.text = "位置を取得中…"

        // queueEvent runs on the same renderer thread as Session.update().  It uses
        // the most recently displayed Frame before another update can move the
        // camera ray away from the pixel the user actually tapped.
        gl.queueEvent { resolveQueuedMark(token) }
    }
'''
new_mark_at = '''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return

        // A new tap invalidates any older attempt, but failed taps are never kept
        // alive. Resolve exactly what the user is looking at right now.
        val token = markAttemptToken + 1L
        markAttemptToken = token
        pendingMark = null

        val frame = latestFrame
        if (frame == null || frame.camera.trackingState != TrackingState.TRACKING) {
            status.text = "ARの準備中です。端末を少し動かしてからもう一度タップしてください"
            return
        }

        val p = try {
            resolveMarkPoint(frame, x, y)
        } catch (_: Throwable) {
            null
        }
        if (p == null) {
            status.text = if (mode == 1) {
                "ボール位置を取得できませんでした。もう一度タップしてください"
            } else {
                "カップ位置を取得できませんでした。もう一度タップしてください"
            }
            return
        }

        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (_: Throwable) {
            null
        }
        if (newAnchor == null) {
            status.text = "位置を固定できませんでした。端末を少し動かしてもう一度タップしてください"
            return
        }

        // applyMark keeps the automatic Ball -> Cup sequence and the v0.8.7
        // Anchor-local slope/arrow coordinate frame intact.
        applyMark(mode, p, newAnchor, token)
    }
'''
replace_once(old_mark_at, new_mark_at, "restore immediate displayed-frame mark resolution")

# The queued resolver remains as dead code from v0.8.10 for patch compatibility,
# but no touch path may invoke it and no failed tap may enter pending state.
mark_start = s.find("    private fun markAt(")
mark_end = s.find("    private fun resolveQueuedMark(")
if mark_start < 0 or mark_end < 0:
    raise SystemExit("v0.8.11 mark function boundaries not found")
mark_body = s[mark_start:mark_end]
if "gl.queueEvent { resolveQueuedMark" in mark_body:
    raise SystemExit("v0.8.11 queued tap resolver still active")
if "PendingMark(mode" in mark_body:
    raise SystemExit("v0.8.11 failed tap can still become pending")
if "applyMark(mode, p, newAnchor, token)" not in mark_body:
    raise SystemExit("v0.8.11 immediate mark application missing")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.11 immediate single-shot marking (v0.8.7 geometry behavior)")
