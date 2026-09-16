from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.10 pattern not found ({label}):\n{old[:1400]}")
    s = s.replace(old, new, 1)


# v0.8.9 correctly moved ARCore operations to the renderer thread, but it kept a
# screen tap alive for up to 2.5 seconds and re-resolved the SAME x/y against later
# camera frames. Once the phone moves, those x/y coordinates point at a different
# physical patch of green. That can displace the ball/cup corridor enough to change
# the fitted cross-slope sign. Bind each tap to the frame currently being displayed:
# queue one renderer-thread operation immediately, use the last renderer Frame once,
# and if it fails ask for a fresh tap instead of chasing stale screen coordinates.
old_mark_at = '''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0) return

        // Do not touch ARCore Frame/Depth/Session from the UI thread.  The renderer
        // consumes this request on the next fresh Frame.
        val token = markAttemptToken + 1L
        markAttemptToken = token
        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime(), token)
        markMode = 0
        status.text = "位置を取得中… 端末を少しだけ動かしてください"
    }
'''
new_mark_at = '''    private fun markAt(x: Float, y: Float) {
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
replace_once(old_mark_at, new_mark_at, "bind tap to displayed frame")

old_retry = '''    private fun tryResolvePendingMark(frame: Frame) {
        val pending = pendingMark ?: return
        if (pending.token != markAttemptToken) {
            if (pendingMark?.token == pending.token) pendingMark = null
            return
        }

        val elapsed = SystemClock.elapsedRealtime() - pending.startedMs
        if (elapsed > 2500L) {
            if (pendingMark?.token == pending.token) pendingMark = null
            runOnUiThread {
                if (pending.token != markAttemptToken) return@runOnUiThread
                markMode = pending.mode
                status.text = if (pending.mode == 1) {
                    "ボール位置を取得できませんでした。端末を少し動かしてもう一度タップしてください"
                } else {
                    "カップ位置を取得できませんでした。端末を少し動かしてもう一度タップしてください"
                }
            }
            return
        }

        // This function runs from onDrawFrame(), so every ARCore operation below is
        // performed on the renderer thread against this exact fresh Frame.
        val p = try {
            resolveMarkPoint(frame, pending.x, pending.y)
        } catch (_: Throwable) {
            null
        } ?: return

        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (_: Throwable) {
            null
        } ?: return

        if (pending.token != markAttemptToken || pendingMark?.token != pending.token) {
            try { newAnchor.detach() } catch (_: Throwable) {}
            return
        }

        pendingMark = null
        runOnUiThread {
            if (pending.token == markAttemptToken) {
                applyMark(pending.mode, p, newAnchor, pending.token)
            } else {
                // Reset may have happened after the renderer posted this callback.
                gl.queueEvent { try { newAnchor.detach() } catch (_: Throwable) {} }
            }
        }
    }
'''
new_retry = '''    private fun resolveQueuedMark(token: Long) {
        val pending = pendingMark ?: return
        if (pending.token != token || token != markAttemptToken) return

        val frame = latestFrame
        if (frame == null || frame.camera.trackingState != TrackingState.TRACKING) {
            if (pendingMark?.token == token) pendingMark = null
            runOnUiThread {
                if (token != markAttemptToken) return@runOnUiThread
                markMode = pending.mode
                status.text = "ARの準備中です。端末を少し動かしてからもう一度タップしてください"
            }
            return
        }

        val p = try {
            resolveMarkPoint(frame, pending.x, pending.y)
        } catch (_: Throwable) {
            null
        }
        if (p == null) {
            if (pendingMark?.token == token) pendingMark = null
            runOnUiThread {
                if (token != markAttemptToken) return@runOnUiThread
                markMode = pending.mode
                status.text = if (pending.mode == 1) {
                    "ボール位置を取得できませんでした。端末を少し動かしてもう一度タップしてください"
                } else {
                    "カップ位置を取得できませんでした。端末を少し動かしてもう一度タップしてください"
                }
            }
            return
        }

        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (_: Throwable) {
            null
        }
        if (newAnchor == null) {
            if (pendingMark?.token == token) pendingMark = null
            runOnUiThread {
                if (token != markAttemptToken) return@runOnUiThread
                markMode = pending.mode
                status.text = "位置を固定できませんでした。端末を少し動かしてもう一度タップしてください"
            }
            return
        }

        if (token != markAttemptToken || pendingMark?.token != token) {
            try { newAnchor.detach() } catch (_: Throwable) {}
            return
        }

        pendingMark = null
        runOnUiThread {
            if (token == markAttemptToken) {
                applyMark(pending.mode, p, newAnchor, token)
            } else {
                gl.queueEvent { try { newAnchor.detach() } catch (_: Throwable) {} }
            }
        }
    }
'''
replace_once(old_retry, new_retry, "single-shot renderer resolution")

# onDrawFrame must not retry a stale x/y against later camera poses.
replace_once(
    '''            if (f.camera.trackingState == TrackingState.TRACKING) {
                tryResolvePendingMark(f)
            }

''',
    '''            // Tap requests are resolved immediately through GLSurfaceView.queueEvent.
            // Never reuse old screen coordinates on later camera frames.

''',
    "remove stale-frame retries",
)

# Clearing latestFrame during reset was needed while the UI thread consumed it.
# It is now renderer-thread-owned. Keeping the last displayed frame lets an immediate
# post-reset tap bind to what the user is actually looking at; the generation token
# still invalidates every pre-reset request.
replace_once(
    '''        markAttemptToken += 1L
        pendingMark = null
        latestFrame = null
        markMode = 1
''',
    '''        markAttemptToken += 1L
        pendingMark = null
        markMode = 1
''',
    "keep displayed frame across reset",
)

if "tryResolvePendingMark(" in s:
    raise SystemExit("v0.8.10 stale multi-frame tap retry remains")
if "gl.queueEvent { resolveQueuedMark(token) }" not in s:
    raise SystemExit("v0.8.10 renderer queue binding missing")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.10 tap-to-displayed-frame binding")
