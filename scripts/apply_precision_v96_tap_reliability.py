"""v9.6: fix initial disabled tap mode and visible tap recovery.

Generated v9.5 started with markMode=0, so the GLSurfaceView touch
listener did NOT accept ACTION_DOWN and ACTION_UP was never delivered.
A later MENU->Re-mark or Next Putt sets markMode=1, which explains why
initial placement works only after other UI operations.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
path=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
s=path.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")
def once(old,new,tag):
    global s
    n=s.count(old)
    if n!=1: raise SystemExit("v9.6 "+tag+" found "+str(n))
    s=s.replace(old,new,1)

once('''    private var markMode = 0
    private var initialBallMarkReady = false''',
'''    // Accept the first Ball touch immediately; if AR tracking is not ready,
    // markAt/renderer gives a diagnostic rather than silently ignoring input.
    @Volatile private var markMode = 1
    private var initialBallMarkReady = false''',
"initial state never 0")
once('''            setOnTouchListener { _, ev ->
                if (ev.action == MotionEvent.ACTION_UP && markMode != 0) {
                    markAt(ev.x, ev.y)
                    true
                } else markMode != 0
            }''',
'''            setOnTouchListener { _, ev ->
                // ACTION_DOWN must be consumed or Android never sends UP.
                // Derive the next marker from real anchors, not stale mode=0.
                if (ev.actionMasked == MotionEvent.ACTION_DOWN) {
                    if (!scanning && !showMap && !showOverlay &&
                        markMode == 0 && (ball == null || cup == null)) {
                        markMode = if (ball == null) 1 else 2
                    }
                    !scanning && !showMap && !showOverlay && markMode != 0
                } else if (ev.actionMasked == MotionEvent.ACTION_UP &&
                    !scanning && !showMap && !showOverlay && markMode != 0) {
                    markAt(ev.x, ev.y)
                    true
                } else if (ev.actionMasked == MotionEvent.ACTION_CANCEL) {
                    markMode != 0
                } else {
                    !scanning && !showMap && !showOverlay && markMode != 0
                }
            }''',
"touch ACTION_DOWN/UP ownership")

once('''        if (mode == 0 || pendingMark != null) return
        val target = if (mode == 1) "ball" else "cup"''',
'''        if (mode == 0) {
            status.text = "位置指定が無効です。MENUからボール再指定を選んでください"
            return
        }
        if (pendingMark != null) {
            status.text = "前のタップを確認中です…"
            return
        }
        val target = if (mode == 1) "ball" else "cup"''',
"clear feedback on ignored tap")
once('''        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime())
        status.text = "位置を取得中…"
        gl.requestRender()''',
'''        val request = PendingMark(mode, x, y, SystemClock.elapsedRealtime())
        pendingMark = request
        status.text = "位置を取得中…"
        // No frame may be delivered while ARCore starts or is temporarily
        // paused. Never leave a permanently pending tap blocking all input.
        status.postDelayed({
            if (pendingMark === request && !scanning) {
                pendingMark = null
                markMode = mode
                precisionTapTrace.append("MARK timeout no fresh renderer frame within 3.5s\\n")
                status.text = "ARの新しいフレームが取得できません。床面を映してから再タップしてください"
                finishPrecisionTap(mode, false)
                restartRenderLoop()
            }
        }, 3500L)
        restartRenderLoop()
        gl.requestRender()''',
"no stuck pending after GL pause")
once('''                status.text = "ARの準備中です。端末を少し動かしてからもう一度タップしてください"
                finishPrecisionTap(mode, false)''',
'''                status.text = "AR追跡が一時停止中です。模様のある床面を映してゆっくり動かし、再タップしてください"
                finishPrecisionTap(mode, false)''',
"explain paused tracking")
once('''                    "ボール位置を取得できませんでした。もう一度タップしてください"
                } else {
                    "カップ位置を取得できませんでした。もう一度タップしてください"
                }
                finishPrecisionTap(mode, false)''',
'''                    "ボール付近のAR面・Depthが不足しています。床面をゆっくり映して再タップしてください"
                } else {
                    "カップ付近のAR面・Depthが不足しています。床面をゆっくり映して再タップしてください"
                }
                finishPrecisionTap(mode, false)''',
"tell user why surface unresolved")

# Never disable the existing anchor validation, tracking gate or slope logic.
assert 'PrecisionMarkerCandidateGate.evaluate(' in s
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in s
assert 'PrecisionMotionEvidenceGate.evaluate(' in s
assert 'PrecisionRepeatScanRecovery.decide(' in s
assert 'precisionFramePoseScanSummary()' in s
assert 'DriveBackupScheduler.onScanSaved(context)' in (
    root/"field/ScanFieldRecorder.kt").read_text()
assert s.count("Precision 9.5") >= 2
s=s.replace("Precision 9.5","Precision 9.6")
assert g.count('versionName = "9.5"') == 1
assert g.count("versionCode = 950") == 1
g=g.replace('versionName = "9.5"','versionName = "9.6"')
g=g.replace("versionCode = 950","versionCode = 960")
path.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v9.6 initial tap mode fixed, DOWN/UP accepted, hung tap bounded")
