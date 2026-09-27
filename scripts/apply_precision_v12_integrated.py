from pathlib import Path

p = Path('app/src/main/java/jp/example/greenreader/MainActivity.kt')
s = p.read_text(encoding='utf-8')

def once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'Precision v1.2 target missing: {label}')
    s = s.replace(old, new, 1)

once(
    'import jp.example.greenreader.ui.GreenMapView\n',
    'import jp.example.greenreader.ui.GreenMapView\n'
    'import jp.example.greenreader.ui.Golfer3DView\n'
    'import jp.example.greenreader.precision.PrecisionDepthCollector\n'
    'import jp.example.greenreader.precision.PrecisionDepthPoint\n'
    'import jp.example.greenreader.precision.PrecisionSurfaceBuilder\n'
    'import jp.example.greenreader.precision.PrecisionSurfaceModel\n'
    'import jp.example.greenreader.precision.PrecisionSlopeAnalyzer\n',
    'imports')

once(
    '    private val collector = DepthCollector()\n',
    '    private val collector = DepthCollector()\n'
    '    private val precisionCollector = PrecisionDepthCollector()\n',
    'parallel collector')

once(
    '    private lateinit var testToggleButton: Button\n',
    '    private lateinit var testToggleButton: Button\n'
    '    private lateinit var view3dToggleButton: Button\n'
    '    private lateinit var view3d: Golfer3DView\n',
    '3d fields')

once(
    '    private var consensusReport: SlopeReport? = null\n',
    '    private var consensusReport: SlopeReport? = null\n'
    '    private val precisionLogPoints = ArrayList<PrecisionDepthPoint>(90000)\n'
    '    private var precisionSurface: PrecisionSurfaceModel? = null\n',
    'precision state')

once(
    '        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }\n'
    '        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))\n',
    '        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }\n'
    '        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))\n\n'
    '        view3d = Golfer3DView(this).apply { visibility = View.GONE }\n'
    '        root.addView(view3d, FrameLayout.LayoutParams(-1, -1))\n',
    '3d view')

once(
    '        panel.addView(row3)\n\n\n        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }\n',
    '        panel.addView(row3)\n\n'
    '        val row4 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }\n'
    '        view3dToggleButton = button("3D目線") { if (view3d.visibility == View.VISIBLE) showCamera() else show3D() }\n'
    '        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, -2, 1f))\n'
    '        panel.addView(row4)\n\n'
    '        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }\n',
    '3d button')

once(
    '        collector.clear()\n        consensusReports.clear()\n        consensusLogPoints.clear()\n',
    '        collector.clear()\n        precisionCollector.clear()\n        consensusReports.clear()\n        consensusLogPoints.clear()\n        precisionLogPoints.clear()\n        precisionSurface = null\n',
    'scan reset')

once(
    '        consensusReport = null\n        collector.clear()\n',
    '        consensusReport = null\n        precisionLogPoints.clear()\n        precisionSurface = null\n        precisionCollector.clear()\n        collector.clear()\n',
    'reset state')

once(
    '        overlayView.clear()\n        capturedBitmap?.recycle()\n',
    '        overlayView.clear()\n        view3d.surface = null\n        view3d.ball = null\n        view3d.cup = null\n        capturedBitmap?.recycle()\n',
    '3d reset')

once(
    '                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)\n',
    '                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)\n'
    '                    precisionCollector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)\n',
    'dual integrate')

s = s.replace(
    '        overlayView.visibility = View.GONE\n        mapView.visibility = View.VISIBLE\n',
    '        overlayView.visibility = View.GONE\n        view3d.visibility = View.GONE\n        mapView.visibility = View.VISIBLE\n', 1)
s = s.replace(
    '        mapView.visibility = View.GONE\n        overlayView.visibility = View.VISIBLE\n',
    '        mapView.visibility = View.GONE\n        view3d.visibility = View.GONE\n        overlayView.visibility = View.VISIBLE\n', 1)

once(
    '    private fun showCamera() {\n',
    '    private fun show3D() {\n'
    '        val surface = precisionSurface\n'
    '        val marks = currentAnalysisMarks()\n'
    '        if (surface == null || marks == null) {\n'
    '            status.text = "3D地形がまだありません。スキャン完了後に表示できます"\n'
    '            return\n'
    '        }\n'
    '        showMap = false\n'
    '        showOverlay = false\n'
    '        gl.visibility = View.GONE\n'
    '        mapView.visibility = View.GONE\n'
    '        overlayView.visibility = View.GONE\n'
    '        view3d.visibility = View.VISIBLE\n'
    '        view3d.surface = surface\n'
    '        view3d.ball = marks.first\n'
    '        view3d.cup = marks.second\n'
    '        view3dToggleButton.text = "カメラ"\n'
    '        suspendArForResult()\n'
    '    }\n\n'
    '    private fun showCamera() {\n',
    'show3d')

once(
    '        mapView.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        gl.visibility = View.VISIBLE\n',
    '        mapView.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        view3d.visibility = View.GONE\n        gl.visibility = View.VISIBLE\n',
    'hide 3d on camera')

once(
    '        val points = collector.snapshot()\n        val room = (60000 - consensusLogPoints.size).coerceAtLeast(0)\n',
    '        val points = collector.snapshot()\n'
    '        val precisionPoints = precisionCollector.snapshot()\n'
    '        val precisionRoom = (90000 - precisionLogPoints.size).coerceAtLeast(0)\n'
    '        if (precisionRoom > 0 && precisionPoints.isNotEmpty()) {\n'
    '            val keep = if (precisionPoints.size <= precisionRoom) precisionPoints else precisionPoints.takeLast(precisionRoom)\n'
    '            precisionLogPoints.addAll(keep)\n'
    '        }\n'
    '        val room = (60000 - consensusLogPoints.size).coerceAtLeast(0)\n',
    'precision window samples')

once(
    '        val candidate = SlopeAnalyzer.analyze(points, marks.first, marks.second)\n',
    '        val precisionCandidate = if (precisionPoints.size >= 250) {\n'
    '            val surface = PrecisionSurfaceBuilder.build(precisionPoints)\n'
    '            PrecisionSlopeAnalyzer.analyze(surface, marks.first, marks.second)\n'
    '        } else null\n'
    '        val candidate = precisionCandidate\n',
    'precision candidate')

once(
    '        collector.clear()\n        consensusWindowIndex += 1\n',
    '        collector.clear()\n        precisionCollector.clear()\n        consensusWindowIndex += 1\n',
    'window clear')

once(
    '        autoStopPending = true\n        captureRequested = true\n        runOnUiThread {\n            status.text = "複数回の測定結果を照合しました。解析中…"\n        }\n',
    '        precisionSurface = if (precisionLogPoints.size >= 500) PrecisionSurfaceBuilder.build(precisionLogPoints) else null\n'
    '        autoStopPending = true\n'
    '        captureRequested = true\n'
    '        runOnUiThread {\n'
    '            status.text = "複数回の測定結果を照合しました。高精度解析中…"\n'
    '        }\n',
    'final surface')

once(
    '        mapView.grain = grain\n',
    '        mapView.grain = grain\n'
    '        precisionSurface?.let { surface ->\n'
    '            view3d.surface = surface\n'
    '            view3d.ball = b\n'
    '            view3d.cup = c\n'
    '        }\n',
    'feed 3d')

s = s.replace('appVersion = "0.8.19"', 'appVersion = "Precision 1.3"')
p.write_text(s, encoding='utf-8')

build = Path('app/build.gradle.kts')
b = build.read_text(encoding='utf-8')
b = b.replace('applicationId = "jp.example.greenreader"', 'applicationId = "jp.showchoo.greenreader.precision"')
b = b.replace('versionCode = 39', 'versionCode = 130')
b = b.replace('versionName = "0.8.19"', 'versionName = "1.3"')
build.write_text(b, encoding='utf-8')

manifest = Path('app/src/main/AndroidManifest.xml')
m = manifest.read_text(encoding='utf-8').replace('android:label="Green Reader"', 'android:label="Green Reader Precision"')
manifest.write_text(m, encoding='utf-8')
print('Applied Precision v1.3 additive integration')
