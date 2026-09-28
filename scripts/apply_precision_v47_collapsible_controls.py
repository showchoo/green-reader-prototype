"""v6.7: compact field UI — remove title HUD and collapse the bottom menu."""
from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")

# 1) Remove the large app-name HUD completely.
hud_start = s.find("        val hud = LinearLayout(this).apply {")
if hud_start < 0:
    raise SystemExit("v6.7 top HUD start missing")
hud_end_marker = '''        root.addView(hud, FrameLayout.LayoutParams(-1, -2).apply {
            gravity = Gravity.TOP
            setMargins(dp(12), dp(10), dp(12), 0)
        })
'''
hud_end = s.find(hud_end_marker, hud_start)
if hud_end < 0:
    raise SystemExit("v6.7 top HUD end missing")
hud_end += len(hud_end_marker)
s = s[:hud_start] + s[hud_end:]

# 2-5) Replace the always-open control panel with:
#      - a small top status chip
#      - a collapsed bottom row (SCAN + MENU)
#      - the existing controls inside an animated expandable container.
panel_start = s.find("        val panel = LinearLayout(this).apply {")
panel_end_marker = '''        ViewCompat.requestApplyInsets(root)
        setContentView(root)
'''
panel_end = s.find(panel_end_marker, panel_start)
if panel_start < 0 or panel_end < 0:
    raise SystemExit("v6.7 panel bounds missing")
panel_end += len(panel_end_marker)

new_panel = r'''        status = TextView(this).apply {
            text = "AR準備中… 端末をゆっくり動かしてください"
            setTextColor(Color.rgb(214, 255, 241))
            textSize = 12.5f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.015f
            setPadding(dp(10), dp(7), dp(10), dp(7))
            background = rounded(
                Color.argb(190, 0, 28, 20),
                Color.argb(175, 52, 255, 192),
                12
            )
            maxWidth = (resources.displayMetrics.widthPixels * 0.82f).toInt()
        }
        root.addView(status, FrameLayout.LayoutParams(-2, -2).apply {
            gravity = Gravity.TOP or Gravity.START
            setMargins(dp(10), dp(10), dp(10), 0)
        })

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(10))
            background = GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                intArrayOf(
                    Color.argb(240, 3, 24, 17),
                    Color.argb(248, 2, 13, 10)
                )
            ).apply {
                cornerRadii = floatArrayOf(
                    dp(22).toFloat(), dp(22).toFloat(),
                    dp(22).toFloat(), dp(22).toFloat(),
                    0f, 0f, 0f, 0f
                )
                setStroke(dp(1), Color.rgb(48, 210, 158))
            }
            elevation = dp(8).toFloat()
        }

        fun button(text: String, action: () -> Unit) = Button(this).apply {
            this.text = text
            isAllCaps = false
            textSize = 11.5f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.015f
            setTextColor(Color.rgb(216, 255, 243))
            stateListAnimator = null
            minHeight = 0
            minimumHeight = 0
            background = GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                intArrayOf(
                    Color.rgb(8, 39, 29),
                    Color.rgb(10, 54, 38)
                )
            ).apply {
                cornerRadius = dp(12).toFloat()
                setStroke(dp(1), Color.rgb(47, 178, 132))
            }
            setPadding(dp(5), dp(2), dp(5), dp(2))
            setOnClickListener { action() }
        }

        // Always-visible compact bar.
        val collapsedBar = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
        }
        val grabber = View(this).apply {
            background = GradientDrawable().apply {
                setColor(Color.argb(210, 112, 255, 213))
                cornerRadius = dp(3).toFloat()
            }
        }
        collapsedBar.addView(grabber, LinearLayout.LayoutParams(dp(42), dp(4)).apply {
            bottomMargin = dp(7)
        })

        val compactRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        scanButton = button("▶  SCAN") { toggleScan() }.apply {
            textSize = 13f
            background = GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                intArrayOf(
                    Color.rgb(43, 247, 164),
                    Color.rgb(93, 255, 202),
                    Color.rgb(33, 218, 151)
                )
            ).apply {
                cornerRadius = dp(13).toFloat()
                setStroke(dp(1), Color.rgb(190, 255, 231))
            }
            setTextColor(Color.rgb(1, 28, 18))
            elevation = dp(3).toFloat()
        }

        val expandedMenu = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
            alpha = 0f
            translationY = dp(12).toFloat()
            setPadding(0, dp(10), 0, 0)
        }

        val expandHandle = TextView(this).apply {
            text = "MENU ︿"
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(104, 255, 204))
            textSize = 11.5f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.04f
            setPadding(dp(12), 0, dp(12), 0)
            background = rounded(
                Color.rgb(5, 34, 25),
                Color.rgb(47, 178, 132),
                12
            )
        }

        var controlsExpanded = false
        fun setControlsExpanded(expanded: Boolean) {
            if (controlsExpanded == expanded) return
            controlsExpanded = expanded
            if (expanded) {
                expandedMenu.visibility = View.VISIBLE
                expandedMenu.animate().cancel()
                expandedMenu.alpha = 0f
                expandedMenu.translationY = dp(12).toFloat()
                expandedMenu.animate()
                    .alpha(1f)
                    .translationY(0f)
                    .setDuration(180L)
                    .start()
                expandHandle.text = "CLOSE ﹀"
            } else {
                expandedMenu.animate().cancel()
                expandedMenu.animate()
                    .alpha(0f)
                    .translationY(dp(12).toFloat())
                    .setDuration(150L)
                    .withEndAction {
                        expandedMenu.visibility = View.GONE
                    }
                    .start()
                expandHandle.text = "MENU ︿"
            }
        }
        expandHandle.setOnClickListener { setControlsExpanded(!controlsExpanded) }
        grabber.setOnClickListener { setControlsExpanded(!controlsExpanded) }

        compactRow.addView(scanButton, LinearLayout.LayoutParams(0, dp(46), 1f).apply {
            rightMargin = dp(8)
        })
        compactRow.addView(expandHandle, LinearLayout.LayoutParams(dp(92), dp(46)))
        collapsedBar.addView(compactRow, LinearLayout.LayoutParams(-1, -2))
        panel.addView(collapsedBar)

        val savedDataLink = TextView(this).apply {
            text = "▸ FIELD RECORDS  /  保存データ"
            setTextColor(Color.rgb(91, 255, 194))
            textSize = 11.5f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.035f
            setPadding(dp(7), dp(5), dp(5), dp(8))
            isClickable = true
            isFocusable = true
            setOnClickListener { openSavedDataFolder() }
        }
        expandedMenu.addView(savedDataLink)

        diagnostics = TextView(this).apply {
            visibility = View.GONE
            setTextColor(0xffd5ffd5.toInt())
            textSize = 12f
            text = "テストモード"
            setPadding(6, 0, 6, 6)
        }
        expandedMenu.addView(diagnostics)

        val row2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row2.addView(button("芝目解析") { analyzeGrain() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        row2.addView(button("解析") { requestCaptureAndAnalyze("実画像を保存して解析中…") }, LinearLayout.LayoutParams(0, dp(42), 1f))
        row2.addView(button("リセット") { resetAll() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        expandedMenu.addView(row2)

        val row3 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        overlayToggleButton = button("実画像") { if (showOverlay) showCamera() else showOverlay() }
        mapToggleButton = button("傾斜マップ") { if (showMap) showCamera() else showMap() }
        testToggleButton = button("診断") { toggleTestMode() }
        row3.addView(overlayToggleButton, LinearLayout.LayoutParams(0, dp(42), 1f))
        row3.addView(mapToggleButton, LinearLayout.LayoutParams(0, dp(42), 1f))
        row3.addView(testToggleButton, LinearLayout.LayoutParams(0, dp(42), 1f))
        expandedMenu.addView(row3)

        val row4 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        view3dToggleButton = button("3D目線") { if (view3d.visibility == View.VISIBLE) showCamera() else show3D() }
        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, dp(42), 1f))
        row4.addView(button("診断コピー") { copyLastPrecisionDiagnostic() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        expandedMenu.addView(row4)

        val row5 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row5.addView(button("精度調整") { showPrecisionTuner() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        row5.addView(button("保存データ再解析") { reanalyzePrecisionSaved() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        expandedMenu.addView(row5)

        panel.addView(expandedMenu)

        val lp = FrameLayout.LayoutParams(-1, -2).apply {
            gravity = Gravity.BOTTOM
            leftMargin = dp(8)
            rightMargin = dp(8)
        }
        root.addView(panel, lp)
        ViewCompat.setOnApplyWindowInsetsListener(root) { _, insets ->
            val navBottom = insets.getInsets(WindowInsetsCompat.Type.navigationBars()).bottom
            val params = panel.layoutParams as FrameLayout.LayoutParams
            params.bottomMargin = navBottom + dp(6)
            panel.layoutParams = params
            insets
        }
        ViewCompat.requestApplyInsets(root)
        setContentView(root)
'''
s = s[:panel_start] + new_panel + s[panel_end:]

# Keep the compact scan label after all state transitions.
s = s.replace('scanButton.text = "スキャン開始"', 'scanButton.text = "▶  SCAN"')
s = s.replace('scanButton.text = "測定中…"', 'scanButton.text = "●  SCANNING"')

# Version bump. Update visible/logging strings from the previous UI build.
s = s.replace("Precision 6.6", "Precision 6.7")

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.6"') != 1 or g.count('versionCode = 660') != 1:
    raise SystemExit("v6.7 Gradle version target missing")
g = g.replace('versionName = "6.6"', 'versionName = "6.7"', 1)
g = g.replace('versionCode = 660', 'versionCode = 670', 1)

assert "GREEN READER  //  PRECISION" not in s
assert "AR SLOPE ENGINE  //  FIELD MODE" not in s
assert 'text = "MENU ︿"' in s
assert "fun setControlsExpanded(expanded: Boolean)" in s
assert "expandedMenu.visibility = View.GONE" in s
assert 'scanButton = button("▶  SCAN")' in s

p.write_text(s, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v6.7 compact collapsible field controls")
# Trigger Precision v6.7 build
