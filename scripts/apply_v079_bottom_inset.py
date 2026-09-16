from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"v0.7.9 pattern not found: {label}")
    s = s.replace(old, new, 1)

replace_once(
    "import androidx.core.content.ContextCompat\n",
    "import androidx.core.content.ContextCompat\nimport androidx.core.view.ViewCompat\nimport androidx.core.view.WindowInsetsCompat\n",
    "window inset imports",
)

replace_once(
    "        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }\n        root.addView(panel, lp)\n",
    "        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }\n"
    "        root.addView(panel, lp)\n"
    "        ViewCompat.setOnApplyWindowInsetsListener(root) { _, insets ->\n"
    "            val navBottom = insets.getInsets(WindowInsetsCompat.Type.navigationBars()).bottom\n"
    "            val params = panel.layoutParams as FrameLayout.LayoutParams\n"
    "            params.bottomMargin = navBottom + dp(8)\n"
    "            panel.layoutParams = params\n"
    "            insets\n"
    "        }\n"
    "        ViewCompat.requestApplyInsets(root)\n",
    "bottom panel navigation-bar inset",
)

path.write_text(s, encoding="utf-8")
print("Applied v0.7.9 bottom control inset")
