"""v6.5: futuristic neon HUD UI, animated result arrows, no measurement logic changes."""
from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f"v6.5 {label}: expected 1, got {s.count(old)}")
    s=s.replace(old,new,1)

once(
    "import jp.example.greenreader.ui.Golfer3DView\n",
    "import jp.example.greenreader.ui.Golfer3DView\nimport jp.example.greenreader.ui.NeonScanOverlayView\n",
    "neon overlay import"
)

once(
    "    private lateinit var view3d: Golfer3DView\n",
    "    private lateinit var view3d: Golfer3DView\n    private lateinit var liveHud: NeonScanOverlayView\n",
    "neon overlay field"
)

once(
'''            gl.requestRender()
            val precisionActive = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (precisionActive) 33L else 250L)
''',
'''            gl.requestRender()
            if (::liveHud.isInitialized && liveHud.scanning != scanning) {
                liveHud.scanning = scanning
            }
            val precisionActive = scanning || captureRequested || pendingMark != null || markMode != 0
            renderHandler.postDelayed(this, if (precisionActive) 33L else 250L)
''',
"hud scan state"
)

once(
'''        root.addView(gl, FrameLayout.LayoutParams(-1, -1))

        mapView = GreenMapView(this).apply { visibility = View.GONE }
''',
'''        root.addView(gl, FrameLayout.LayoutParams(-1, -1))

        liveHud = NeonScanOverlayView(this)
        root.addView(liveHud, FrameLayout.LayoutParams(-1, -1))

        mapView = GreenMapView(this).apply { visibility = View.GONE }
''',
"live hud layer"
)

old_hud='''        val hud = LinearLayout(this).apply {
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
'''
new_hud='''        val hud = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(11), dp(16), dp(11))
            background = GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                intArrayOf(
                    Color.argb(232, 1, 22, 16),
                    Color.argb(218, 2, 43, 30),
                    Color.argb(232, 1, 17, 13)
                )
            ).apply {
                cornerRadius = dp(18).toFloat()
                setStroke(dp(1), Color.rgb(61, 255, 194))
            }
            addView(TextView(this@MainActivity).apply {
                text = "GREEN READER  //  PRECISION v6.5"
                setTextColor(Color.rgb(105, 255, 205))
                textSize = 12f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                letterSpacing = 0.09f
                setShadowLayer(8f, 0f, 0f, Color.rgb(0, 255, 180))
            })
            addView(TextView(this@MainActivity).apply {
                text = "AR SLOPE ENGINE  //  FIELD MODE"
                setTextColor(Color.rgb(225, 255, 246))
                textSize = 17f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                letterSpacing = 0.03f
                setPadding(0, dp(2), 0, 0)
            })
            addView(View(this@MainActivity).apply {
                background = GradientDrawable(
                    GradientDrawable.Orientation.LEFT_RIGHT,
                    intArrayOf(
                        Color.TRANSPARENT,
                        Color.rgb(60, 255, 195),
                        Color.TRANSPARENT
                    )
                )
            }, LinearLayout.LayoutParams(-1, dp(1)).apply { topMargin = dp(7) })
        }
'''
once(old_hud,new_hud,"top neon hud")

old_panel='''        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(16))
            background = GradientDrawable().apply {
                cornerRadii = floatArrayOf(dp(28).toFloat(), dp(28).toFloat(), dp(28).toFloat(), dp(28).toFloat(), 0f, 0f, 0f, 0f)
                setColor(Color.argb(242, 6, 17, 12))
                setStroke(dp(1), Color.rgb(45, 77, 59))
            }
        }
'''
new_panel='''        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(15), dp(13), dp(15), dp(16))
            background = GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                intArrayOf(
                    Color.argb(246, 3, 24, 17),
                    Color.argb(248, 2, 14, 10)
                )
            ).apply {
                cornerRadii = floatArrayOf(
                    dp(26).toFloat(), dp(26).toFloat(),
                    dp(26).toFloat(), dp(26).toFloat(),
                    0f, 0f, 0f, 0f
                )
                setStroke(dp(1), Color.rgb(48, 210, 158))
            }
            elevation = dp(10).toFloat()
        }
'''
once(old_panel,new_panel,"bottom hud panel")

old_status='''        status = TextView(this).apply {
            text = "AR準備中… 端末をゆっくり動かしてください"
            setTextColor(Color.rgb(211, 234, 218))
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(5), dp(2), dp(5), dp(10))
        }
'''
new_status='''        status = TextView(this).apply {
            text = "AR準備中… 端末をゆっくり動かしてください"
            setTextColor(Color.rgb(214, 255, 241))
            textSize = 13.5f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.02f
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = rounded(
                Color.argb(205, 0, 32, 23),
                Color.argb(190, 52, 255, 192),
                12
            )
        }
'''
once(old_status,new_status,"status chip")

old_saved='''        val savedDataLink = TextView(this).apply {
            text = "保存データを開く  ›"
            setTextColor(Color.rgb(117, 255, 167))
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(5), 0, dp(5), dp(8))
'''
new_saved='''        val savedDataLink = TextView(this).apply {
            text = "▸ FIELD RECORDS  /  保存データ"
            setTextColor(Color.rgb(91, 255, 194))
            textSize = 12f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.04f
            setPadding(dp(7), dp(7), dp(5), dp(7))
'''
once(old_saved,new_saved,"saved data link")

old_button='''        fun button(text: String, action: () -> Unit) = Button(this).apply {
            this.text = text
            isAllCaps = false
            textSize = 12.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = rounded(Color.rgb(21, 43, 32), Color.rgb(54, 96, 70), 15)
            setPadding(dp(5), 0, dp(5), 0)
            setOnClickListener { action() }
        }
'''
new_button='''        fun button(text: String, action: () -> Unit) = Button(this).apply {
            this.text = text
            isAllCaps = false
            textSize = 11.8f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.02f
            setTextColor(Color.rgb(216, 255, 243))
            stateListAnimator = null
            background = GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                intArrayOf(
                    Color.rgb(8, 39, 29),
                    Color.rgb(10, 54, 38)
                )
            ).apply {
                cornerRadius = dp(13).toFloat()
                setStroke(dp(1), Color.rgb(47, 178, 132))
            }
            setPadding(dp(5), 0, dp(5), 0)
            setOnClickListener { action() }
        }
'''
once(old_button,new_button,"neon button")

old_scan='''        scanButton = button("スキャン開始") { toggleScan() }.apply {
            background = rounded(Color.rgb(83, 225, 130), Color.rgb(149, 255, 183), 15)
            setTextColor(Color.rgb(5, 31, 15))
        }
'''
new_scan='''        scanButton = button("▶  SCAN  /  スキャン開始") { toggleScan() }.apply {
            textSize = 13f
            background = GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                intArrayOf(
                    Color.rgb(43, 247, 164),
                    Color.rgb(93, 255, 202),
                    Color.rgb(33, 218, 151)
                )
            ).apply {
                cornerRadius = dp(14).toFloat()
                setStroke(dp(1), Color.rgb(190, 255, 231))
            }
            setTextColor(Color.rgb(1, 28, 18))
            elevation = dp(4).toFloat()
        }
'''
once(old_scan,new_scan,"primary scan button")

# Keep the live overlay only over the camera.
for old,new,label in [
(
'''        showMap = true
        showOverlay = false
        gl.visibility = View.GONE
''',
'''        showMap = true
        showOverlay = false
        liveHud.visibility = View.GONE
        gl.visibility = View.GONE
''',
"hide hud map"
),
(
'''        showMap = false
        showOverlay = true
        gl.visibility = View.GONE
''',
'''        showMap = false
        showOverlay = true
        liveHud.visibility = View.GONE
        gl.visibility = View.GONE
''',
"hide hud overlay"
),
(
'''        showMap = false
        showOverlay = false
        mapView.visibility = View.GONE
''',
'''        showMap = false
        showOverlay = false
        liveHud.visibility = View.VISIBLE
        mapView.visibility = View.GONE
''',
"show live hud"
)
]:
    once(old,new,label)

# 3D view also hides the live camera HUD.
needle='''        gl.visibility = View.GONE
        mapView.visibility = View.GONE
        overlayView.visibility = View.GONE
        view3d.visibility = View.VISIBLE
'''
if needle in s:
    s=s.replace(
        needle,
        '''        liveHud.visibility = View.GONE
        gl.visibility = View.GONE
        mapView.visibility = View.GONE
        overlayView.visibility = View.GONE
        view3d.visibility = View.VISIBLE
''',
        1
    )

# Version bump. v6.4 appears in visible and field logging metadata; all should follow the UI build.
s=s.replace('Precision 6.4','Precision 6.5')
gpath=Path("app/build.gradle.kts")
g=gpath.read_text(encoding="utf-8")
if g.count('versionName = "6.4"') != 1 or g.count('versionCode = 640') != 1:
    raise SystemExit("v6.5 gradle version target missing")
g=g.replace('versionName = "6.4"','versionName = "6.5"',1)
g=g.replace('versionCode = 640','versionCode = 650',1)

assert "NeonScanOverlayView" in s
assert "AR SLOPE ENGINE  //  FIELD MODE" in s
assert "liveHud.visibility = View.GONE" in s
assert "if (::liveHud.isInitialized && liveHud.scanning != scanning)" in s
assert "Precision 6.5" in s

p.write_text(s,encoding="utf-8")
gpath.write_text(g,encoding="utf-8")
print("Applied Precision v6.5 futuristic neon HUD UI")
# Trigger Precision v6.5 build
