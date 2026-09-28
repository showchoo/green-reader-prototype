"""v5.7: resolve taps on the fresh renderer Frame and add Depth diagnostics/fallback."""
from pathlib import Path
p=Path('app/src/main/java/jp/example/greenreader/MainActivity.kt')
s=p.read_text()

def get_function(name):
    start=s.index(f'    private fun {name}(')
    end=s.index('\n    private fun ',start+20)
    return start,end,s[start:end]

def replace_function(name, body):
    global s
    start,end,_=get_function(name)
    s=s[:start]+body.rstrip()+'\n'+s[end:]

def once(old,new,label):
    global s
    if s.count(old)!=1:
        raise SystemExit(f'{label}: expected 1 got {s.count(old)}')
    s=s.replace(old,new,1)

replace_function('markAt', r'''    private fun markAt(x: Float, y: Float) {
        val mode = markMode
        if (mode == 0 || pendingMark != null) return
        val target = if (mode == 1) "ball" else "cup"
        precisionTapTrace = StringBuilder(
            "Precision 5.7 TAP $target queued x=$x y=$y mode=$mode uiLatestTimestamp=${latestFrame?.timestamp}\n"
        )
        pendingMark = PendingMark(mode, x, y, SystemClock.elapsedRealtime())
        status.text = "位置を取得中…"
        gl.requestRender()
    }
''')

once('''            val f = s.update()
            latestFrame = f
            trackingStateText = f.camera.trackingState.name
''','''            val f = s.update()
            latestFrame = f
            trackingStateText = f.camera.trackingState.name
            resolvePrecisionPendingTap(f)
''','fresh frame call')

marker='    private fun tryResolvePendingMark(frame: Frame) {'
idx=s.index(marker)
helper=r'''    private fun resolvePrecisionPendingTap(frame: Frame) {
        val pending = pendingMark ?: return
        pendingMark = null
        val mode = pending.mode
        val target = if (mode == 1) "ball" else "cup"
        val waited = SystemClock.elapsedRealtime() - pending.startedMs
        precisionTapTrace.append(
            "freshFrame timestamp=${frame.timestamp} waitMs=$waited tracking=${frame.camera.trackingState} " +
                "world=${frame.camera.pose.translation.contentToString()} viewport=${viewportW}x${viewportH}\n"
        )
        if (frame.camera.trackingState != TrackingState.TRACKING) {
            precisionTapTrace.append("MARK fresh-frame-not-tracking reason=${frame.camera.trackingFailureReason}\n")
            runOnUiThread {
                status.text = "ARの準備中です。端末を少し動かしてからもう一度タップしてください"
                finishPrecisionTap(mode, false)
            }
            return
        }
        if (mode == 2) {
            val reference = ballAnchor
            precisionTapTrace.append(
                "ball reference tracking=${reference?.trackingState} world=${reference?.pose?.translation?.contentToString()}\n"
            )
            if (reference?.trackingState != TrackingState.TRACKING) {
                runOnUiThread {
                    status.text = "ボール位置の追跡を確認できません。追跡復帰後にカップをタップしてください"
                    finishPrecisionTap(mode, false)
                }
                return
            }
        }

        var point = resolveMarkPoint(frame, pending.x, pending.y)
        if (point == null) {
            point = tracedMarkCandidate(frame, "neighborDepth") {
                ballPointFromNeighborDepth(frame, pending.x, pending.y)
            }
            if (point != null) precisionTapTrace.append("selected source=neighborDepth\n")
        } else {
            precisionTapTrace.append("neighborDepth=not-needed\n")
        }
        if (point == null) {
            point = tracedMarkCandidate(frame, "rawDepth") {
                rawDepthPointNearTap(frame, pending.x, pending.y)
            }
            if (point != null) precisionTapTrace.append("selected source=rawDepth\n")
        } else {
            precisionTapTrace.append("rawDepth=not-needed\n")
        }

        if (point == null) {
            precisionTapTrace.append("MARK tap-unresolved target=$target on-fresh-frame\n")
            runOnUiThread {
                status.text = if (mode == 1) {
                    "ボール位置を取得できませんでした。もう一度タップしてください"
                } else {
                    "カップ位置を取得できませんでした。もう一度タップしてください"
                }
                finishPrecisionTap(mode, false)
            }
            return
        }

        runOnUiThread {
            applyMark(mode, point)
        }
    }

'''
s=s[:idx]+helper+s[idx:]

# detailed trace inside exact Full Depth helper
start,end,fn=get_function('depthPointAtTap')
old='''                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                val plane = img.planes[0]
'''
new='''                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                precisionTapTrace.append(
                    "fullDepth exact image=${img.width}x${img.height} tex=($tx,$ty) px=($px,$py) timestamp=${img.timestamp}\\n"
                )
                val plane = img.planes[0]
'''
if fn.count(old)!=1: raise SystemExit('exact coord target')
fn=fn.replace(old,new,1)
old='''                if (bestX < 0) return null

                val values = ArrayList<Int>(25)
'''
new='''                if (bestX < 0) {
                    precisionTapTrace.append("fullDepth exact no-valid-depth radius<=4 range=200..12000mm\\n")
                    return null
                }
                precisionTapTrace.append("fullDepth exact chosen=($bestX,$bestY) mm=$bestMm d2=$bestD2\\n")

                val values = ArrayList<Int>(25)
'''
if fn.count(old)!=1: raise SystemExit('exact no data target')
fn=fn.replace(old,new,1)
old='''                if (!u.isFinite() || !v.isFinite() ||
                    u < 0f || v < 0f || u >= dims[0].toFloat() || v >= dims[1].toFloat()) {
                    return null
                }
'''
new='''                if (!u.isFinite() || !v.isFinite() ||
                    u < 0f || v < 0f || u >= dims[0].toFloat() || v >= dims[1].toFloat()) {
                    precisionTapTrace.append(
                        "fullDepth exact imageCoord-invalid uv=($u,$v) imageDims=${dims.contentToString()}\\n"
                    )
                    return null
                }
'''
if fn.count(old)!=1: raise SystemExit('exact uv target')
fn=fn.replace(old,new,1)
s=s[:start]+fn+s[end:]

# neighbor Full Depth trace
start,end,fn=get_function('ballPointFromNeighborDepth')
old='''                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                val plane = img.planes[0]
'''
new='''                val px = (tx * img.width).toInt()
                val py = (ty * img.height).toInt()
                precisionTapTrace.append(
                    "fullDepth neighbor image=${img.width}x${img.height} tex=($tx,$ty) px=($px,$py) timestamp=${img.timestamp}\\n"
                )
                val plane = img.planes[0]
'''
if fn.count(old)!=1: raise SustemExit('neighbor coord target')
fn=fn.replace(old,new,1)
old='''                if (!found || values.size < 6) return null
'''
new='''                if (!found || values.size < 6) {
                    precisionTapTrace.append("fullDepth neighbor no-valid-cluster radius=5..12 lastSamples=${values.size}\\n")
                    return null
                }
'''
if fn.count(old)!=1: raise SystemExit('neighbor no data target')
fn=fn.replace(old,new,1)
old='''                val z = clustered[clustered.size / 2] / 1000f
                if (z > 4.0f) return null
'''
new='''                val z = clustered[clustered.size / 2] / 1000f
                precisionTapTrace.append(
                    "fullDepth neighbor samples=${values.size} clustered=${clustered.size} medianMm=$median z=$z\\n"
                )
                if (z > 4.0f) return null
'''
if fn.count(old)!=1: raise SystemExit('neighbor z trace target')
fn=fn.replace(old,new,1)
s=s[:start]+fn+s[end:]

# Raw Depth fallback helper
marker='    private fun analyzeGrain() {'
idx=s.index(marker)
raw=r'''    private fun rawDepthPointNearTap(frame: Frame, x: Float, y: Float): Vec3? {
        if (viewportW <= 1 || viewportH <= 1) return null
        return try {
            frame.acquireRawDepthImage16Bits().use { depth ->
                frame.acquireRawDepthConfidenceImage().use { confidence ->
                    val view = floatArrayOf(
                        (x / viewportW).coerceIn(0f, 1f),
                        (y / viewportH).coerceIn(0f, 1f)
                    )
                    val tex = FloatArray(2)
                    frame.transformCoordinates2d(
                        Coordinates2d.VIEW_NORMALIZED,
                        view,
                        Coordinates2d.TEXTURE_NORMALIZED,
                        tex
                    )
                    if (!tex[0].isFinite() || !tex[1].isFinite()) {
                        precisionTapTrace.append("rawDepth tex-invalid=${tex.contentToString()}\n")
                        return null
                    }
                    val tx = tex[0].coerceIn(0f, 0.9999f)
                    val ty = tex[1].coerceIn(0f, 0.9999f)
                    val px = (tx * depth.width).toInt()
                    val py = (ty * depth.height).toInt()
                    val dp = depth.planes[0]
                    val db = dp.buffer.order(ByteOrder.LITTLE_ENDIAN)
                    val cp = confidence.planes[0]
                    val cb = cp.buffer
                    precisionTapTrace.append(
                        "rawDepth image=${depth.width}x${depth.height} tex=($tx,$ty) px=($px,$py) timestamp=${depth.timestamp}\n"
                    )

                    var chosen: List<Int>? = null
                    var chosenRadius = -1
                    var maxSamples = 0
                    for (radius in 0..20) {
                        val values = ArrayList<Int>()
                        val inner = kotlin.math.max(0, radius - 3)
                        val outer2 = radius * radius
                        val inner2 = inner * inner
                        for (dy in -radius..radius) {
                            for (dx in -radius..radius) {
                                val d2 = dx * dx + dy * dy
                                if (radius > 0 && (d2 > outer2 || d2 < inner2)) continue
                                val xx = px + dx
                                val yy = py + dy
                                if (xx !in 0 until depth.width || yy !in 0 until depth.height) continue
                                val di = yy * dp.rowStride + xx * dp.pixelStride
                                if (di + 1 >= db.limit()) continue
                                val mm = java.lang.Short.toUnsignedInt(db.getShort(di))
                                if (mm !in 200..4000) continue
                                val cx = (xx * confidence.width / depth.width).coerceIn(0, confidence.width - 1)
                                val cy = (yy * confidence.height / depth.height).coerceIn(0, confidence.height - 1)
                                val ci = cy * cp.rowStride + cx * cp.pixelStride
                                if (ci >= cb.limit()) continue
                                val conf = cb.get(ci).toInt() and 0xff
                                if (conf < 128) continue
                                values += mm
                            }
                        }
                        if (values.size > maxSamples) maxSamples = values.size
                        if (values.size >= 3) {
                            chosen = values
                            chosenRadius = radius
                            break
                        }
                    }
                    val values = chosen ?: run {
                        precisionTapTrace.append("rawDepth no-confident-samples radius<=20 maxSamples=$maxSamples\n")
                        return null
                    }
                    val sorted = values.sorted()
                    val medianMm = sorted[sorted.size / 2]
                    val z = medianMm / 1000f

                    val intr = frame.camera.textureIntrinsics
                    val focal = intr.focalLength
                    val principal = intr.principalPoint
                    val dims = intr.imageDimensions
                    val fx = focal[0] * depth.width.toFloat() / dims[0].toFloat()
                    val fy = focal[1] * depth.height.toFloat() / dims[1].toFloat()
                    val cx = principal[0] * depth.width.toFloat() / dims[0].toFloat()
                    val cy = principal[1] * depth.height.toFloat() / dims[1].toFloat()
                    if (!fx.isFinite() || !fy.isFinite() || fx <= 0f || fy <= 0f) return null
                    val u = tx * depth.width.toFloat()
                    val v = ty * depth.height.toFloat()
                    val xCam = z * (u - cx) / fx
                    val yCam = z * (cy - v) / fy
                    val world = frame.camera.pose.transformPoint(floatArrayOf(xCam, yCam, -z))
                    precisionTapTrace.append(
                        "rawDepth selected radius=$chosenRadius samples=${values.size} medianMm=$medianMm world=${world.contentToString()}\n"
                    )
                    Vec3(world[0], world[1], world[2])
                }
            }
        } catch (e: Exception) {
            precisionTapTrace.append("rawDepthPointNearTap error=${e.javaClass.simpleName}: ${e.message}\n")
            null
        }
    }

'''
s=s[:idx]+raw+s[idx:]

s=s.replace('appVersion = "Precision 5.6"','appVersion = "Precision 5.7"',1)

# assertions
assert 'resolvePrecisionPendingTap(f)' in s
_,_,mark=get_function('markAt')
assert 'resolveMarkPoint(' not in mark
assert 'pendingMark = PendingMark' in mark
assert 'markMode = 0' not in mark
assert s.count('private fun rawDepthPointNearTap')==1
assert s.count('private fun resolvePrecisionPendingTap')==1
gradle=Path('app/build.gradle.kts')
g=gradle.read_text(encoding='utf-8')
if g.count('versionName = \"5.6\"') != 1 or g.count('versionCode = 560') != 1:
    raise SystemExit('v5.7 Gradle version target missing')
g=g.replace('versionName = \"5.6\"', 'versionName = \"5.7\"', 1)
g=g.replace('versionCode = 560', 'versionCode = 570', 1)
p.write_text(s, encoding='utf-8')
gradle.write_text(g, encoding='utf-8')
print('Applied Precision v5.7 fresh-frame tap resolution + Depth diagnostics')
# Trigger Precision v5.7 build
