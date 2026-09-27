from pathlib import Path

p = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"Precision v3.3 target missing: {label}")
    s = s.replace(old, new, 1)

once(
    '        panel.addView(row4)\n',
    '        panel.addView(row4)\n'
    '        val row5 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }\n'
    '        row5.addView(button("精度調整") { showPrecisionTuner() }, LinearLayout.LayoutParams(0, -2, 1f))\n'
    '        row5.addView(button("保存データ再解析") { reanalyzePrecisionSaved() }, LinearLayout.LayoutParams(0, -2, 1f))\n'
    '        panel.addView(row5)\n',
    'tuning buttons'
)

once(
    '    private fun show3D() {\n',
    r'''    private fun showPrecisionTuner() {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28, 12, 28, 8)
        }

        fun seekRow(
            label: String,
            max: Int,
            progress: Int,
            valueText: (Int) -> String
        ): Pair<TextView, SeekBar> {
            val tv = TextView(this).apply {
                text = label + ": " + valueText(progress)
                textSize = 15f
                setPadding(0, 10, 0, 0)
            }
            val sb = SeekBar(this).apply {
                this.max = max
                this.progress = progress.coerceIn(0, max)
                setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                    override fun onProgressChanged(seekBar: SeekBar?, p: Int, fromUser: Boolean) {
                        tv.text = label + ": " + valueText(p)
                    }
                    override fun onStartTrackingTouch(seekBar: SeekBar?) {}
                    override fun onStopTrackingTouch(seekBar: SeekBar?) {}
                })
            }
            box.addView(tv)
            box.addView(sb)
            return tv to sb
        }

        val (_, mad) = seekRow(
            "MAD上限", 90,
            ((PrecisionSurfaceBuilder.tuningMaxMadMeters - 0.01f) * 1000f).toInt(),
            { p -> String.format("%.0f mm", 10f + p) }
        )
        val (_, band) = seekRow(
            "高さ帯", 25,
            ((PrecisionSurfaceBuilder.tuningBaseHeightBandMeters - 0.05f) * 100f).toInt(),
            { p -> String.format("%.0f cm", 5f + p) }
        )
        val (_, reach) = seekRow(
            "連結距離", 5,
            (PrecisionSurfaceBuilder.tuningNeighborReach - 2),
            { p -> (p + 2).toString() + "セル" }
        )
        val (_, step) = seekRow(
            "段差許容", 80,
            ((PrecisionSurfaceBuilder.tuningStepBaseMeters - 0.02f) * 1000f).toInt(),
            { p -> String.format("%.0f mm", 20f + p) }
        )
        val (_, med) = seekRow(
            "中央値許容", 80,
            ((PrecisionSurfaceBuilder.tuningMedianToleranceMeters - 0.02f) * 1000f).toInt(),
            { p -> String.format("%.0f mm", 20f + p) }
        )
        val (_, nbr) = seekRow(
            "最低近傍数", 4,
            (PrecisionSurfaceBuilder.tuningLocalMinNeighbors - 1),
            { p -> (p + 1).toString() + "点" }
        )

        val scroll = ScrollView(this).apply { addView(box) }
        android.app.AlertDialog.Builder(this)
            .setTitle("Precision 精度調整")
            .setMessage("保存済みDepthを使うため、再スキャンせず調整できます。")
            .setView(scroll)
            .setNeutralButton("標準に戻す") { _, _ ->
                PrecisionSurfaceBuilder.resetTuning()
                reanalyzePrecisionSaved()
            }
            .setNegativeButton("閉じる", null)
            .setPositiveButton("適用して再解析") { _, _ ->
                PrecisionSurfaceBuilder.tuningMaxMadMeters = (10f + mad.progress) / 1000f
                PrecisionSurfaceBuilder.tuningBaseHeightBandMeters = (5f + band.progress) / 100f
                PrecisionSurfaceBuilder.tuningNeighborReach = reach.progress + 2
                PrecisionSurfaceBuilder.tuningStepBaseMeters = (20f + step.progress) / 1000f
                PrecisionSurfaceBuilder.tuningMedianToleranceMeters = (20f + med.progress) / 1000f
                PrecisionSurfaceBuilder.tuningLocalMinNeighbors = nbr.progress + 1
                reanalyzePrecisionSaved()
            }
            .show()
    }

    private fun reanalyzePrecisionSaved() {
        val marks = currentAnalysisMarks()
        if (marks == null) {
            status.text = "再解析できません: ボール/カップ位置がありません"
            return
        }
        if (precisionLogPoints.size < 250) {
            status.text = "再解析できません: 保存Depth点が不足しています (" + precisionLogPoints.size + ")"
            return
        }

        val surface = PrecisionSurfaceBuilder.build(precisionLogPoints)
        precisionSurface = surface
        val report = PrecisionSlopeAnalyzer.analyze(surface, marks.first, marks.second)
        view3d.surface = surface
        view3d.ball = marks.first
        view3d.cup = marks.second

        if (report == null) {
            status.text = "再解析NG ground=" + surface.groundCellCount + " / " +
                PrecisionSurfaceBuilder.tuningSummary()
            precisionLastDiagnostic =
                "再解析 surface=[" + PrecisionSurfaceBuilder.lastDiagnostic +
                "] analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"
            if (testMode) {
                diagnostics.visibility = View.VISIBLE
                diagnostics.text = precisionLastDiagnostic
            }
            return
        }

        mapView.report = report
        status.text = String.format(
            "再解析OK: %.2fm / 縦 %.1f%% / 横 %.1f%% / ground=%d",
            report.distanceMeters,
            report.overallLongitudinalPercent,
            report.overallCrossPercent,
            surface.groundCellCount
        )
        precisionLastDiagnostic =
            "再解析OK surface=[" + PrecisionSurfaceBuilder.lastDiagnostic +
            "] analyzer=[" + PrecisionSlopeAnalyzer.lastDiagnostic + "]"
        showMap()
    }

    private fun show3D() {
''',
    'tuner functions'
)

p.write_text(s, encoding="utf-8")
print("Applied Precision v3.3 runtime tuning UI")
