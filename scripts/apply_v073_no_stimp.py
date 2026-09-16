from pathlib import Path

path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = path.read_text(encoding="utf-8")

s = s.replace("    private lateinit var stimp: SeekBar\n    private lateinit var stimpLabel: TextView\n", "")

start = s.find("        stimpLabel = TextView(this).apply {")
end_marker = "        panel.addView(stimp)\n"
if start != -1:
    end = s.find(end_marker, start)
    if end == -1:
        raise SystemExit("Stimp UI block end not found")
    end += len(end_marker)
    s = s[:start] + s[end:]
else:
    raise SystemExit("Stimp UI block start not found")

s = s.replace("        val st = 7f + stimp.progress / 10f\n", "        val st = 9.0f\n")

path.write_text(s, encoding="utf-8")
print("Removed Stimp UI; internal default fixed at 9.0")
