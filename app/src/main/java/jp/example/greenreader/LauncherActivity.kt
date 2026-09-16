package jp.example.greenreader

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class LauncherActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(8, 18, 14)
        window.navigationBarColor = Color.rgb(8, 18, 14)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(24), dp(52), dp(24), dp(28))
            background = GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                intArrayOf(Color.rgb(8, 18, 14), Color.rgb(18, 52, 36), Color.rgb(7, 15, 12))
            )
        }

        val kicker = TextView(this).apply {
            text = "GREEN READER  /  AR LAB"
            setTextColor(Color.rgb(124, 255, 177))
            textSize = 13f
            letterSpacing = 0.18f
            typeface = Typeface.DEFAULT_BOLD
        }
        root.addView(kicker)

        root.addView(TextView(this).apply {
            text = "Read the green.\nSee the line."
            setTextColor(Color.WHITE)
            textSize = 35f
            typeface = Typeface.DEFAULT_BOLD
            setLineSpacing(0f, 0.94f)
            setPadding(0, dp(18), 0, dp(10))
        })

        root.addView(TextView(this).apply {
            text = "傾斜解析と芝目フィールド記録を、現場で迷わず使える形にまとめました。"
            setTextColor(Color.rgb(202, 219, 209))
            textSize = 15f
            setPadding(0, 0, 0, dp(30))
        })

        root.addView(cardButton("GREEN SCAN", "傾斜・実画像ライン解析", true) {
            startActivity(Intent(this, MainActivity::class.java))
        })
        root.addView(space())
        root.addView(cardButton("GRAIN FIELD LOG", "芝目画像 + 角度 + 信頼度 + 端末姿勢を保存", false) {
            startActivity(Intent(this, GrainFieldActivity::class.java))
        })

        root.addView(TextView(this).apply {
            text = "FIELD DATA → Pictures/GreenReaderRecords\nCSV → Download/GreenReaderRecords"
            setTextColor(Color.rgb(132, 158, 143))
            textSize = 12f
            setPadding(0, dp(28), 0, 0)
        })

        setContentView(root)
    }

    private fun cardButton(title: String, subtitle: String, accent: Boolean, action: () -> Unit): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(20), dp(22), dp(20))
            background = GradientDrawable().apply {
                cornerRadius = dp(22).toFloat()
                setColor(if (accent) Color.rgb(68, 207, 116) else Color.argb(230, 23, 42, 33))
                setStroke(dp(1), if (accent) Color.rgb(133, 255, 172) else Color.rgb(58, 92, 73))
            }
            isClickable = true
            isFocusable = true
            elevation = dp(8).toFloat()
            setOnClickListener { action() }
            addView(TextView(this@LauncherActivity).apply {
                text = title
                setTextColor(if (accent) Color.rgb(5, 28, 14) else Color.WHITE)
                textSize = 19f
                typeface = Typeface.DEFAULT_BOLD
                letterSpacing = 0.08f
            })
            addView(TextView(this@LauncherActivity).apply {
                text = subtitle
                setTextColor(if (accent) Color.rgb(13, 70, 34) else Color.rgb(185, 207, 194))
                textSize = 14f
                setPadding(0, dp(6), 0, 0)
            })
            layoutParams = LinearLayout.LayoutParams(-1, -2)
        }
    }

    private fun space() = View(this).apply { layoutParams = LinearLayout.LayoutParams(1, dp(14)) }
    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()
}
