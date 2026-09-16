from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.9 pattern not found ({label}):\n{old[:1200]}")
    s = s.replace(old, new, 1)


# v0.8.8 still resolved the first tap on the Android UI thread using latestFrame,
# while retries used the current Frame on the GL renderer thread. ARCore Frame/depth
# access and Session.createAnchor must not bounce between those two execution paths.
# A UI tap now records only coordinates/mode; the next renderer frame performs the
# complete depth/hit-test/Anchor operation.
old_mark_at = '''    private fun markAt(x: Float, y: Float) {
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
new_mark_at = '''    private fun markAt(x: Float, y: Float) {
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
replace_once(old_mark_at, new_mark_at, "queue taps instead of reading latestFrame on UI")


old_retry = '''    private fun tryResolvePendingMark(frame: Frame) {
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
new_retry = '''    private fun tryResolvePendingMark(frame: Frame) {
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
replace_once(old_retry, new_retry, "resolve and anchor only on renderer thread")


old_apply = '''    private fun applyMark(mode: Int, p: Vec3, token: Long) {
        if (token != markAttemptToken) return
        pendingMark = null
        val newAnchor = try {
            session?.createAnchor(Pose.makeTranslation(p.x, p.y, p.z))
        } catch (_: Throwable) {
            null
        }
        if (newAnchor == null) {
            markMode = mode
            status.text = "位置を固定できませんでした。端末を少し動かしてもう一度タップしてください"
            return
        }

        collector.clear()
        if (mode == 1) {
            ballAnchor?.detach()
            ballAnchor = newAnchor
            ball = p
            markMode = 2
            status.text = "次にカップをタップしてください"
        } else {
            cupAnchor?.detach()
            cupAnchor = newAnchor
            cup = p
            markMode = 0
            status.text = "設定完了。スキャン開始を押してください"
        }
        if (testMode) updateDiagnostics()
    }
'''
new_apply = '''    private fun applyMark(mode: Int, p: Vec3, newAnchor: Anchor, token: Long) {
        if (token != markAttemptToken) {
            gl.queueEvent { try { newAnchor.detach() } catch (_: Throwable) {} }
            return
        }
        pendingMark = null
        collector.clear()
        if (mode == 1) {
            val oldAnchor = ballAnchor
            ballAnchor = newAnchor
            ball = p
            markMode = 2
            status.text = "次にカップをタップしてください"
            if (oldAnchor != null) gl.queueEvent { try { oldAnchor.detach() } catch (_: Throwable) {} }
        } else {
            val oldAnchor = cupAnchor
            cupAnchor = newAnchor
            cup = p
            markMode = 0
            status.text = "設定完了。スキャン開始を押してください"
            if (oldAnchor != null) gl.queueEvent { try { oldAnchor.detach() } catch (_: Throwable) {} }
        }
        if (testMode) updateDiagnostics()
    }
'''
replace_once(old_apply, new_apply, "UI only accepts renderer-created Anchor")


# Reset must also stop touching Anchor native state on the UI thread.  Clear the UI
# references immediately, and perform detach on the renderer thread.
replace_once(
    '''        ballAnchor?.detach()
        cupAnchor?.detach()
        ballAnchor = null
        cupAnchor = null
        ball = null
        cup = null
''',
    '''        val oldBallAnchor = ballAnchor
        val oldCupAnchor = cupAnchor
        ballAnchor = null
        cupAnchor = null
        if (oldBallAnchor != null || oldCupAnchor != null) {
            gl.queueEvent {
                try { oldBallAnchor?.detach() } catch (_: Throwable) {}
                try { oldCupAnchor?.detach() } catch (_: Throwable) {}
            }
        }
        ball = null
        cup = null
''',
    "detach reset anchors on renderer thread",
)

# Guard against accidental reintroduction of cross-thread mark resolution.
if "val f = latestFrame\n        if (f == null)" in s[s.find("private fun markAt"):s.find("private fun tryResolvePendingMark")]:
    raise SystemExit("v0.8.9 markAt still reads latestFrame")
if "session?.createAnchor" in s[s.find("private fun applyMark"):s.find("private fun resolveMarkPoint")]:
    raise SystemExit("v0.8.9 applyMark still creates Anchor on UI thread")

path.write_text(s, encoding="utf-8")
print("Applied v0.8.9 renderer-thread-only mark acquisition")
