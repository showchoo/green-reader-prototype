from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

start=s.find("    private fun applyMark(mode: Int, p: Vec3) {")
end=s.find("\n    private fun ", start + 20)
if start < 0 or end < 0:
    raise SystemExit("v5.2 applyMark boundaries missing")

new_apply=r'''    private fun applyMark(mode: Int, p: Vec3) {
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

        // Validate a cup mark immediately against the already-fixed ball.
        // Previously an implausible cup was accepted and only rejected after
        // an 8-second scan timeout.
        if (mode == 2) {
            val bAnchor = ballAnchor
            if (bAnchor != null && bAnchor.trackingState == TrackingState.TRACKING) {
                val levelFrame = GravityAlignedFrame.fromPose(bAnchor.pose)
                val bt = levelFrame.worldToLocal(bAnchor.pose.translation)
                val ct = levelFrame.worldToLocal(newAnchor.pose.translation)
                val dx = ct[0] - bt[0]
                val dz = ct[2] - bt[2]
                val horizontal = kotlin.math.sqrt(dx * dx + dz * dz)
                val vertical = kotlin.math.abs(ct[1] - bt[1])
                val limit = kotlin.math.max(0.08f, horizontal * 0.12f + 0.04f)

                if (!horizontal.isFinite() || !vertical.isFinite() || vertical > limit) {
                    precisionLastDiagnostic =
                        "MARK rejected-at-tap horizontal=" + String.format("%.3f", horizontal) +
                        " vertical=" + String.format("%.3f", vertical) +
                        " limit=" + String.format("%.3f", limit) +
                        " ball=(" + String.format("%.2f", bt[0]) + "," +
                            String.format("%.2f", bt[1]) + "," + String.format("%.2f", bt[2]) + ")" +
                        " cup=(" + String.format("%.2f", ct[0]) + "," +
                            String.format("%.2f", ct[1]) + "," + String.format("%.2f", ct[2]) + ")"
                    newAnchor.detach()
                    markMode = 2
                    status.text = "カップ位置の高さが不自然です。カップをもう一度タップしてください"
                    return
                }
            }
        }

        markMode = 0
        collector.clear()
        if (mode == 1) {
            ballAnchor?.detach()
            ballAnchor = newAnchor
            ball = p
            status.text = "ボール位置を設定しました。次にカップを設定"
        } else {
            cupAnchor?.detach()
            cupAnchor = newAnchor
            cup = p
            status.text = "カップ位置を設定しました。スキャン開始してください"
        }
        if (testMode) updateDiagnostics()
    }
'''
s=s[:start]+new_apply+s[end:]
p.write_text(s,encoding="utf-8")
print("Applied Precision v5.2 immediate cup sanity validation")
