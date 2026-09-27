from pathlib import Path

ROOT = Path('.')
main_path = ROOT / 'app/src/main/java/jp/example/greenreader/MainActivity.kt'
depth_path = ROOT / 'app/src/main/java/jp/example/greenreader/analysis/DepthCollector.kt'
build_path = ROOT / 'app/build.gradle.kts'
manifest_path = ROOT / 'app/src/main/AndroidManifest.xml'

# Replace the post-v0.8.19 DepthCollector implementation while preserving its public API.
depth_path.write_text(r'''package jp.example.greenreader.analysis

import com.google.ar.core.Coordinates2d
import com.google.ar.core.Frame
import com.google.ar.core.Pose
import com.google.ar.core.TrackingState
import com.google.ar.core.exceptions.NotYetAvailableException
import jp.example.greenreader.precision.PrecisionDepthPoint
import java.nio.ByteOrder
import kotlin.math.max

/**
 * High-precision Raw Depth collector. Public methods intentionally match v0.8.19
 * so the proven UI, logging, tap handling and consensus workflow remain intact.
 */
class DepthCollector(
    private val confidenceThreshold: Int = 160
) {
    private val samples = ArrayList<PrecisionDepthPoint>(70000)
    private val frameTimestamps = LinkedHashSet<Long>()
    private var lastRawTimestamp = Long.MIN_VALUE

    @Synchronized fun clear() {
        samples.clear()
        frameTimestamps.clear()
        lastRawTimestamp = Long.MIN_VALUE
    }

    @Synchronized fun size(): Int = samples.size
    @Synchronized fun uniqueFrames(): Int = frameTimestamps.size
    @Synchronized fun snapshot(): List<Vec3> = samples.map { Vec3(it.x, it.y, it.z) }
    @Synchronized fun snapshotPrecision(): List<PrecisionDepthPoint> = samples.toList()

    @Synchronized
    fun integrate(
        frame: Frame,
        referencePose: Pose,
        pixelStrideStep: Int = 4,
        minDepthM: Float = 0.25f,
        maxDepthM: Float = 5f
    ) {
        val camera = frame.camera
        if (camera.trackingState != TrackingState.TRACKING) return

        try {
            frame.acquireRawDepthImage16Bits().use { depth ->
                val timestamp = depth.timestamp
                if (timestamp == lastRawTimestamp) return

                frame.acquireRawDepthConfidenceImage().use { confidence ->
                    lastRawTimestamp = timestamp
                    val dPlane = depth.planes[0]
                    val cPlane = confidence.planes[0]
                    val dBuf = dPlane.buffer.order(ByteOrder.LITTLE_ENDIAN)
                    val cBuf = cPlane.buffer
                    val cameraPose = camera.pose
                    val worldToReference = referencePose.inverse()
                    val intr = camera.imageIntrinsics
                    val focal = intr.focalLength
                    val principal = intr.principalPoint
                    val dims = intr.imageDimensions
                    val imageW = dims[0].toFloat()
                    val imageH = dims[1].toFloat()
                    val step = max(2, pixelStrideStep)

                    val capacity = ((depth.width + step - 1) / step) * ((depth.height + step - 1) / step)
                    val textureCoords = FloatArray(capacity * 2)
                    val depths = FloatArray(capacity)
                    val confs = FloatArray(capacity)
                    var count = 0

                    for (y in 0 until depth.height step step) {
                        for (x in 0 until depth.width step step) {
                            val di = y * dPlane.rowStride + x * dPlane.pixelStride
                            if (di + 1 >= dBuf.limit()) continue
                            val mm = java.lang.Short.toUnsignedInt(dBuf.getShort(di))
                            if (mm == 0) continue
                            val meters = mm / 1000f
                            if (meters !in minDepthM..maxDepthM) continue

                            val confX = (x * confidence.width / depth.width).coerceIn(0, confidence.width - 1)
                            val confY = (y * confidence.height / depth.height).coerceIn(0, confidence.height - 1)
                            val ci = confY * cPlane.rowStride + confX * cPlane.pixelStride
                            if (ci >= cBuf.limit()) continue
                            val conf = cBuf.get(ci).toInt() and 0xff
                            if (conf < confidenceThreshold) continue

                            val o = count * 2
                            textureCoords[o] = (x + 0.5f) / depth.width.toFloat()
                            textureCoords[o + 1] = (y + 0.5f) / depth.height.toFloat()
                            depths[count] = meters
                            confs[count] = conf / 255f
                            count++
                        }
                    }
                    if (count == 0) return@use

                    val imageCoords = FloatArray(count * 2)
                    frame.transformCoordinates2d(
                        Coordinates2d.TEXTURE_NORMALIZED,
                        textureCoords.copyOf(count * 2),
                        Coordinates2d.IMAGE_PIXELS,
                        imageCoords
                    )

                    for (i in 0 until count) {
                        val u = imageCoords[i * 2]
                        val v = imageCoords[i * 2 + 1]
                        if (!u.isFinite() || !v.isFinite()) continue
                        if (u < 0f || v < 0f || u >= imageW || v >= imageH) continue
                        val z = depths[i]
                        val camX = (u - principal[0]) / focal[0] * z
                        val camY = -(v - principal[1]) / focal[1] * z
                        val world = cameraPose.transformPoint(floatArrayOf(camX, camY, -z))
                        val local = worldToReference.transformPoint(world)
                        samples += PrecisionDepthPoint(
                            local[0], local[1], local[2], confs[i], timestamp
                        )
                    }
                    frameTimestamps += timestamp
                    if (samples.size > 90000) {
                        samples.subList(0, samples.size - 70000).clear()
                    }
                }
            }
        } catch (_: NotYetAvailableException) {
            // Raw Depth is intentionally sparse and is not produced for every camera frame.
        } catch (_: Throwable) {
            // A single malformed frame must never break the on-course workflow.
        }
    }
}
''', encoding='utf-8')

s = main_path.read_text(encoding='utf-8')

def replace_once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'Precision v1.2 pattern not found: {label}')
    s = s.replace(old, new, 1)

replace_once(
    'import jp.example.greenreader.ui.GreenMapView\n',
    'import jp.example.greenreader.ui.GreenMapView\n'
    'import jp.example.greenreader.ui.Golfer3DView\n'
    'import jp.example.greenreader.precision.PrecisionDepthPoint\n'
    'import jp.example.greenreader.precision.PrecisionSurfaceBuilder\n'
    'import jp.example.greenreader.precision.PrecisionSurfaceModel\n'
    'import jp.example.grenreader.precision.PrecisionSlopeAnalyzer\n',
    'precision imports'
)
replace_once(
    '    private lateinit var testToggleButton: Button\n',
    '    private lateinit var testToggleButton: Button\n'
    '    private lateinit var view3dToggleButton: Button\n'
    '    private lateinit var view3d: Golfer3DView\n',
    '3d fields'
)
replace_once(
    '    private var consensusReport: SlopeReport? = null\n',
    '    private var consensusReport: SlopeReport? = null\n'
    '    private val precisionLogPoints = ArrayList<PrecisionDepthPoint>(90000)\n'
    '    private var precisionSurface: PrecisionSurfaceModel? = null\n',
    'precision state'
)
replace_once(
    ''''        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }\n        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))\n''',
    ''''        overlayView = CameraOverlayResultView(this).apply { visibility = View.GONE }\n        root.addView(overlayView, FrameLayout.LayoutParams(-1, -1))\n\n        view3d = Golfer3DView(this).apply { visibility = View.GONE }\n        root.addView(view3d, FrameLayout.LayoutParams(-1, -1))\n''',
    '3d view creation'
)
replace_once(
    '''        row3.addView(testToggleButton, LinearLayout.LayoutParams(0, -2, 1f))\n        panel.addView(row3)\n\n\n        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }\n'' ,
    '''        row3.addView(testToggleButton, LinearLayout.LayoutParams(0, -2, 1f))\n        panel.addView(row3)\n\n        val row4 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }\n        view3dToggleButton = button("3D宻線") { if (view3d.visibility == View.VISIBLEY ) showCamera() else show3D() }\n        row4.addView(view3dToggleButton, LinearLayout.LayoutParams(0, -2, 1f))\n        panel.addView(row4)\n\n        val lp = FrameLayout.LayoutParams(-1, -2).apply { gravity = Gravity.BOTTOM }\n''',
    '3d control row'
)
replace_once(
    ''''        consensusReports.clear()\n        consensusLogPoints.clear()\n        consensusWindowIndex = 0\n''',
    ''''        consensusReports.clear()\n        consensusLogPoints.clear()\n        precisionLogPoints.clear()\n        precisionSurface = null\n        consensusWindowIndex = 0\n''',
    'scan precision reset'
)
replace_once(
    '''        consensusWindowStartedMs = 0L\n        consensusReport = null\n        collector.clear()\n''',
    ''''        consensusWindowStartedMs = 0L\n        consensusReport = null\n        precisionLogPoints.clear()\n        precisionSurface = null\n        collector.clear()\n ''',
    'full reset precision state'
)
replace_once(
    '''        overlayView.clear()\n        capturedBitmap?.recycle()\n''',
    ''''        overlayView.clear()\n        view3d.surface = null\n        view3d.ball = null\n        view3d.cup = null\n        capturedBitmap?.recycle()\n''',
    'clear 3d state'
)
# Hide 3D when other result screens are selected.
s = s.replace(
    '''        gl.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        mapView.visibility = View.VISIBLE\n''',
    '''        gl.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        view3d.visibility = View.GONE\n        mapView.visibility = View.VISIBLE\n''', 1
)
s = s.replace(
    '''        gl.visibility = View.GONE\n        mapView.visibility = View.GONE\n        overlayView.visibility = View.VISIBLE\n''',
    ''''        gl.visibility = View.GONE\n        mapView.visibility = View.GONE\n        view3d.visibility = View.GONE\n        overlayView.visibility = View.VISIBLE\n ''', 1
)
replace_once(
    '    private fun showCamera() {\n',
     ''''    private fun show3D() {\n        val surface = precisionSurface\n        val marks = currentAnalysisMarks()\n        if (surface == null || marks == null) {\n            status.text = "3D地形がまだありません。スキャン完了後に表示できません"\n            return\n        }\n        showMap = false\n        showOverlay = false\n        gl.visibility = View.GONE\n        mapView.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        view3d.visibility = View.VISIBLE\n        view3d.surface = surface\n        view3d.ball = marks.first\n        view3d.cup = marks.second\n        view3dToggleButton.text = "カメラ"\n        suspendArForResult()\n    }\n\n    private fun showCamera() {\n ''',
    'show3D function'
)
replace_once(
    '''        mapView.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        gl.visibility = View.VISIBLE\n        mapToggleButton.text = "倾斜マップ"\n        overlayToggleButton.text = "実画像"\n''',
    ''''        mapView.visibility = View.GONE\n        overlayView.visibility = View.GONE\n        view3d.visibility = View.GONE\n        gl.visibility = View.VISIBLE\n        mapToggleButton.text = "傾斜マップ"\n        overlayToggleButton.text = "実画像"\n        view3dToggleButton.text = "3D目線"\n''',
    'camera hides 3d'
)
replace_once(
    '''        val points = collector.snapshot()\n        val room = (60000 - consensusLogPoints.size).coerceAtLeast(0)\n        if (room > 0 && points.isNotEmpty()) {\n            val toKeep = if (points.size <= room) points else points.takeLast(room)\n            consensusLogPoints.addAll(toKeep)\n        }\n\n        val candidate = SlopeAnalyzer.analyze(points, marks.first, marks.second)\n        if (candidate != null && candidate.pointCount >= 80) {\n            consensusReports += candidate\n        }\n ''',
    ''''        val points = collector.snapshot()\n        val precisionPoints = collector.snapshotPrecision()\n        val room = (60000 - consensusLogPoints.size).coerceAtLeast(0)\n        if (room > 0 && points.isNotEmpty()) {\n            val toKeep = if (points.size <= room) points else points.takeLast(room)\n            consensusLogPoints.addAll(toKeep)\n        }\n        val precisionRoom = (90000 - precisionLogPoints.size).coerceAtLeast(0)\n        if (precisionRoom > 0 && precisionPoints.isNotEmpty()) {\n            val toKeep = if (precisionPoints.size <= precisionRoom) precisionPoints else precisionPoints.takeLast(precisionRoom)\n            precisionLogPoints.addAll(toKeep)\n        }\n\n        val precisionCandidate = if (precisionPoints.size >= 250) {\n            val surface = PrecisionSurfaceBuilder.build(precisionPoints)\n            PrecisionSlopeAnalyzer.analyze(surface, marks.first, marks.second)\n        } else null\n        val candidate = precisionCandidate ?: SlopeAnalyzer.analyze(points, marks.first, marks.second)\n        if (candidate != null && candidate.pointCount >= 80) {\n            consensusReports += candidate\n        }\n ''',
    'precision window analysis'
)
replace_once(
    ''''        autoStopPending = true\n        captureRequested = true\n        runOnUiThread {\n            status.text = "複数回の測定結果を照合しました。解析中…"\n        }\n''',
    ''''        precisionSurface = if (precisionLogPoints.size >= 500) {\n            PrecisionSurfaceBuilder.build(precisionLogPoints)\n        } else null\n\n        autoStopPending = true\n        captureRequested = true\n        runOnUiThread {\n            status.text = "複数回の測定結果を照合しました。高精度解析中…"\n        }\n ''',
    'final precision surface'
)
replace_once(
    '''        mapView.report = report\n        mapView.advice = adv\n        mapView.grain = grain\n ''',
    ''''        mapView.report = report\n        mapView.advice = adv\n        mapView.grain = grain\n        precisionSurface?.let { surface ->\n            view3d.surface = surface\n            view3d.ball = b\n            view3d.cup = c\n        }\n ''',
    'feed 3d view'
)
replace_once(
    '''        diagnostics.text = "TEST  AR:$trackingStateText  Depth:${if (depthSupported) "対応" else "非対応"}  点:${collector.size()}  Ball:$b  Cup:$c  Tap:$wait  Scan:${if (scanning) "ON" else "OFF"}  Shot:$shot"\n''',
    '''        val cells = precisionSurface?.cells?.size ?: 0\n        diagnostics.text = "TEST  AR:$trackingStateText  Depth:${if (depthSupported) "対応" else "非対応"}  点:${collector.size()}  RawF:${collector.uniqueFrames()}  Cell:$cells  Ball:$b  Cup:$c  Tap:$wait  Scan:${if (scanning) "ON" else "OFF"}  Shot:$shot"\n''',
    'precision diagnostics'
)
s = s.replace('appVersion = "0.8.19"', 'appVersion = "Precision 1.2"')
main_path.write_text(s, encoding='utf-8')

build = build_path.read_text(encoding='utf-8')
build = build.replace('applicationId = "jp.example.greenreader"', 'applicationId = "jp.showchoo.greenreader.precision"')
build = build.replace('versionCode = 39', 'versionCode = 120')
build = build.replace('versionName = "0.8.19"', 'versionName = "1.2"')
build_path.write_text(build, encoding='utf-8')

manifest = manifest_path.read_text(encoding='utf-8')
manifest = manifest.replace('android:label="Green Reader"', 'android:label="Green Reader Precision"')
manifest_path.write_text(manifest, encoding='utf-8')

print('Applied Precision v1.2 on top of fully patched v0.8.19')
