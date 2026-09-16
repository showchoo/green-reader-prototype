from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.8 pattern not found ({label}):\n{old[:1000]}")
    s = s.replace(old, new, 1)


# A failed mark is retried on the GL thread and then delivered back to the UI thread.
# Merely clearing pendingMark during reset is not enough: a retry can already have
# captured the old PendingMark and enqueue a stale UI callback after reset. Give each
# tap attempt a monotonically increasing token. Reset/pause increments the token so
# every callback from the old generation becomes a no-op.
replace_once(
    """    private data class PendingMark(val mode: Int, val x: Float, val y: Float, val startedMs: Long)
    @Volatile private var pendingMark: PendingMark? = null
""",
    """    private data class PendingMark(
        val mode: Int,
        val x: Float,
        val y: Float,
        val startedMs: Long,
        val token: Long
    )
    @Volatile private var pendingMark: PendingMark? = null
    @Volatile private var markAttemptToken = 0L
""",
    "mark attempt generation",
)

# v0.7.4/v0.7.5 insert logging reset fields between captureRequested and pendingMark,
# so anchor directly on the final pendingMark/markMode pair produced by v0.8.2.
# Reset is a hard boundary for mark acquisition. Drop latestFrame as well so an
# immediate post-reset tap cannot resolve against the pre-reset camera frame.
replace_once(
    """        pendingMark = null
        markMode = 1
""",
    """        markAttemptToken += 1L
        pendingMark = null
        latestFrame = null
        markMode = 1
""",
    "hard reset tap acquisition",
)

# Backgrounding the app is another lifecycle boundary. Invalidate callbacks that may
# already be queued from the GL thread and discard the pre-pause frame. If a mark was
# still incomplete, restore the correct target so the user can tap again after resume.
replace_once(
    """    override fun onPause() {
        super.onPause()
        scanning = false
        pendingMark = null
        gl.onPause()
        session?.pause()
    }
""",
    """    override fun onPause() {
        super.onPause()
        scanning = false
        markAttemptToken += 1L
        pendingMark = null
        latestFrame = null
        if (ball == null || cup == null) {
            markMode = if (ball == null) 1 else 2
        }
        gl.onPause()
        session?.pause()
    }
""",
    "pause invalidates mark callbacks",
)

old_mark_at = '''    private fun markAt(x: Float, y: Float) {
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
new_mark_at = '''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return
        val f = latestFrame
        if (f == null) {
            status.text = "ARの準備中です。端末を少し動かしてください"
            return
        }

        val token = markAttemptToken + 1L
        markAttemptToken = token
        val p = resolveMarkPoint(f, x, y)
        if (p != null) {
            applyMark(mode, p, token)
            return
        }

        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime(), token)
        markMode = 0
        status.text = "位置を取得中… そのまま端末を少しだけ動かしてください"
    }
'''
replace_once(old_mark_at, new_mark_at, "tokenize each tap")

old_retry = '''    private fun tryResolvePendingMark(frame: Frame) {
        val pending = pendingMark ?: return
        val elapsed = SystemClock.elapsedRealtime() - pending.startedMs
        if (elapsed > 1800L) {
            pendingMark = null
            markMode = pending.mode
            runOnUiThread {
                status.text = if (pending.mode == 1) {
                    "ボール位置を取得できませんでした。もう一度1回だけタップしてください"
                } else {
                    "カップ位置を取得できませんでした。もう一度1回だけタップしてください"
                }
            }
            return
        }

        val p = resolveMarkPoint(frame, pending.x, pending.y) ?: return
        pendingMark = null
        runOnUiThread { applyMark(pending.mode, p) }
    }
'''
new_retry = '''    private fun tryResolvePendingMark(frame: Frame) {
        val pending = pendingMark ?: return
        if (pending.token != markAttemptToken) {
            if (pendingMark?.token == pending.token) pendingMark = null
            return
        }

        val elapsed = SystemClock.elapsedRealtime() - pending.startedMs
        if (elapsed > 1800L) {
            if (pendingMark?.token == pending.token) pendingMark = null
            runOnUiThread {
                // Reset or a newer tap may have happened after the GL thread queued
                // this callback. Never revive an old mark mode/status in that case.
                if (pending.token != markAttemptToken) return@runOnUiThread
                markMode = pending.mode
                status.text = if (pending.mode == 1) {
                    "ボール位置を取得できませんでした。もう一度1回だけタップしてください"
                } else {
                    "カップ位置を取得できませんでした。もう一度1回だけタップしてください"
                }
            }
            return
        }

        val p = resolveMarkPoint(frame, pending.x, pending.y) ?: return
        if (pending.token != markAttemptToken || pendingMark?.token != pending.token) return
        pendingMark = null
        runOnUiThread {
            if (pending.token == markAttemptToken) {
                applyMark(pending.mode, p, pending.token)
            }
        }
    }
'''
replace_once(old_retry, new_retry, "ignore stale retry callbacks")

# v0.8.1 creates Anchors here and v0.8.2 controls the Ball -> Cup automatic sequence.
# Guard that existing logic with the same token, so a resolved old retry cannot create
# an Anchor or alter markMode after reset.
replace_once(
    """    private fun applyMark(mode: Int, p: Vec3) {
        pendingMark = null
""",
    """    private fun applyMark(mode: Int, p: Vec3, token: Long) {
        if (token != markAttemptToken) return
        pendingMark = null
""",
    "apply mark only for current generation",
)

# Static safety checks: all mark application must now carry a token and no legacy
# PendingMark constructor may remain after the transformation.
if "applyMark(mode, p)" in s or "applyMark(pending.mode, p)" in s:
    raise SystemExit("v0.8.8 stale applyMark caller remains")
if "PendingMark(mode, x, y, SystemClock.elapsedRealtime())" in s:
    raise SystemExit("v0.8.8 stale PendingMark constructor remains")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.8 reset-safe tap acquisition state")
