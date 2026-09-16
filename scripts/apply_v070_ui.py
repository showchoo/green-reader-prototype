from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.7 UI pattern not found:\n{old[:240]}")
    s = s.replace(old, new, 1)

replace_once(
    "import android.graphics.Bitmap\nimport android.graphics.PointF",
    "import android.graphics.Bitmap\nimport android.graphics.Color\nimport android.graphics.PointF\nimport android.graphics.Typeface\nimport android.graphics.drawable.GradientDrawable",
)

replace_once(
    """        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }
        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))

        val panel = LinearLayout(this).apply {""",
    """        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }
        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))

        val hud = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(11), dp(16), dp(11))
            background = rounded(Color.argb(215, 5, 18, 13), Color.argb(210, 74, 145, 101), 20)
            addView(TextView(this@MainActivity).apply {
                text = "GREEN READER  /  ライブスキャン"
                setTextColor(Color.rgb(117, 255, 167))
                textSize = 12f
                typeface = Typeface.DEFAULT_BOLD
                letterSpacing = 0.08f
            })
            addView(TextView(this@MainActivity).apply {
                text = "傾斜を読む。狙いを決める。"
                setTextColor(Color.WHITE)
                textSize = 19f
                typeface = Typeface.DEFAULT_BOLD
                setPadding(0, dp(2), 0, 0)
            })
        }
        root.addView(hud, FrameLayout.LayoutParams(-1, -2).apply {
            gravity = Gravity.TOP
            setMargins(dp(12), dp(10), dp(12), 0)
        })

        val panel = LinearLayout(this).apply {""",
)

replace_once(
    """            orientation = LinearLayout.VERTICAL
            setPadding(14, 12, 14, 14)
            setBackgroundColor(0xD8111111.toInt())""",
    """            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(16))
            background = GradientDrawable().apply {
                cornerRadii = floatArrayOf(dp(28).toFloat(), dp(28).toFloat(), dp(28).toFloat(), dp(28).toFloat(), 0f, 0f, 0f, 0f)
                setColor(Color.argb(242, 6, 17, 12))
                setStroke(dp(1), Color.rgb(45, 77, 59))
            }""",
)

replace_once(
    """        status = TextView(this).apply {
            text = \"①ボール ②カップ ③スキャン開始\"
            setTextColor(0xffffffff.toInt())
            textSize = 16f
            setPadding(6, 4, 6, 8)
        }""",
    """        status = TextView(this).apply {
            text = "① ボール → ② カップ → ③ スキャン"
            setTextColor(Color.rgb(211, 234, 218))
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(5), dp(2), dp(5), dp(10))
        }""",
)

replace_once(
    """        fun button(text: String, action: () -> Unit) = Button(this).apply {
            this.text = text
            isAllCaps = false
            setOnClickListener { action() }
        }""",
    """        fun button(text: String, action: () -> Unit) = Button(this).apply {
            this.text = text
            isAllCaps = false
            textSize = 12.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = rounded(Color.rgb(21, 43, 32), Color.rgb(54, 96, 70), 15)
            setPadding(dp(5), 0, dp(5), 0)
            setOnClickListener { action() }
        }""",
)

replace_once('button("ボール") {', 'button("● ボール") {')
replace_once('button("カップ") {', 'button("◎ カップ") {')
replace_once('scanButton = button("スキャン開始") { toggleScan() }', 'scanButton = button("スキャン開始") { toggleScan() }.apply { background = rounded(Color.rgb(83, 225, 130), Color.rgb(149, 255, 183), 15); setTextColor(Color.rgb(5, 31, 15)) }')
replace_once('row2.addView(button("芝目解析")', 'row2.addView(button("芝目解析")')
replace_once('row2.addView(button("解析")', 'row2.addView(button("解析")')
replace_once('row2.addView(button("リセット")', 'row2.addView(button("リセット")')
replace_once('overlayToggleButton = button("実画像結果")', 'overlayToggleButton = button("実画像")')
replace_once('mapToggleButton = button("傾斜マップ")', 'mapToggleButton = button("傾斜マップ")')
replace_once('testToggleButton = button("テストモード")', 'testToggleButton = button("診断")')

replace_once(
    """        stimpLabel = TextView(this).apply {
            setTextColor(0xffffffff.toInt())
            text = \"Stimp: 9.0\"
        }""",
    """        stimpLabel = TextView(this).apply {
            setTextColor(Color.rgb(139, 255, 178))
            text = "グリーン速度   STIMP 9.0"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = 0.05f
            setPadding(dp(5), dp(8), dp(5), 0)
        }""",
)
replace_once('stimpLabel.text = String.format("Stimp: %.1f", 7f + p / 10f)', 'stimpLabel.text = String.format("グリーン速度   STIMP %.1f", 7f + p / 10f)')

# Keep existing dynamic button text readable after styling.
s = s.replace('scanButton.text = "スキャン終了"', 'scanButton.text = "スキャン終了"')
s = s.replace('scanButton.text = "スキャン開始"', 'scanButton.text = "スキャン開始"')
s = s.replace('mapToggleButton.text = "カメラ表示"', 'mapToggleButton.text = "カメラ"')
s = s.replace('overlayToggleButton.text = "カメラ表示"', 'overlayToggleButton.text = "カメラ"')
s = s.replace('mapToggleButton.text = "傾斜マップ"', 'mapToggleButton.text = "傾斜マップ"')
s = s.replace('overlayToggleButton.text = "実画像結果"', 'overlayToggleButton.text = "実画像"')
s = s.replace('testToggleButton.text = if (testMode) "テストOFF" else "テストモード"', 'testToggleButton.text = if (testMode) "診断OFF" else "診断"')

replace_once(
    """    override fun onRequestPermissionsResult(req: Int, perms: Array<out String>, res: IntArray) {""",
    """    private fun rounded(fill: Int, stroke: Int, radiusDp: Int) = GradientDrawable().apply {
        cornerRadius = dp(radiusDp).toFloat()
        setColor(fill)
        setStroke(dp(1), stroke)
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    override fun onRequestPermissionsResult(req: Int, perms: Array<out String>, res: IntArray) {""",
)

path.write_text(s, encoding="utf-8")
print("Applied v0.7 Japanese scan UI refresh")
