from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.8.2 pattern not found ({label}):\n{old[:700]}")
    s = s.replace(old, new, 1)


replace_once(
    "    private var markMode = 0\n",
    "    private var markMode = 1\n",
    "initial mark mode",
)

replace_once(
    '            text = "① ボール → ② カップ → ③ スキャン"\n',
    '            text = "ボールをタップしてください"\n',
    "initial status",
)

old_row = '''        val row1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row1.addView(button("● ボール") {
            showCamera()
            pendingMark = null
            markMode = 1
            status.text = "ボールの中心付近を1回タップしてください"
        }, LinearLayout.LayoutParams(0, -2, 1f))
        row1.addView(button("◎ カップ") {
            showCamera()
            pendingMark = null
            markMode = 2
            status.text = "カップの中心付近を1回タップしてください"
        }, LinearLayout.LayoutParams(0, -2, 1f))
        scanButton = button("スキャン開始") { toggleScan() }.apply { background = rounded(Color.rgb(83, 225, 130), Color.rgb(149, 255, 183), 15); setTextColor(Color.rgb(5, 31, 15)) }
        row1.addView(scanButton, LinearLayout.LayoutParams(0, -2, 1.25f))
        panel.addView(row1)
'''
new_row = '''        val row1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        scanButton = button("スキャン開始") { toggleScan() }.apply {
            background = rounded(Color.rgb(83, 225, 130), Color.rgb(149, 255, 183), 15)
            setTextColor(Color.rgb(5, 31, 15))
        }
        row1.addView(scanButton, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(row1)
'''
replace_once(old_row, new_row, "remove mark buttons")

replace_once(
    '''        markMode = 0
        scanButton.text = "スキャン開始"
''',
    '''        markMode = 1
        scanButton.text = "スキャン開始"
''',
    "reset mark mode",
)
replace_once(
    '        status.text = "リセットしました。ボール位置から設定してください"\n',
    '        status.text = "ボールをタップしてください"\n',
    "reset status",
)

old_apply = '''        markMode = 0
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
'''
new_apply = '''        collector.clear()
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
'''
replace_once(old_apply, new_apply, "automatic ball-to-cup sequence")

replace_once(
    '                status.text = "先にボールとカップを設定してください"\n',
    '                status.text = if (ball == null) "ボールをタップしてください" else "カップをタップしてください"\n',
    "scan guidance",
)

path.write_text(s, encoding="utf-8")
print("Applied v0.8.2 automatic ball-to-cup marking sequence")
