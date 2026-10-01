"""v7.1: automatically save a camera frame for failed scans too."""
from pathlib import Path

main_path = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
recorder_path = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt")
gradle_path = Path("app/build.gradle.kts")

s = main_path.read_text(encoding="utf-8")
r = recorder_path.read_text(encoding="utf-8")
g = gradle_path.read_text(encoding="utf-8")

def replace_private_function(src: str, name: str, replacement: str) -> str:
    start = src.index(f"    private fun {name}(")
    candidates = [
        src.find("\n    private fun ", start + 20),
        src.find("\n    fun ", start + 20),
    ]
    ends = [x for x in candidates if x >= 0]
    if not ends:
        raise SystemExit(f"v7.1 next function not found after {name}")
    end = min(ends)
    return src[:start] + replacement.rstrip() + "\n" + src[end:]

def replace_object_function(src: str, name: str, replacement: str) -> str:
    start = src.index(f"    fun {name}(")
    candidates = [
        src.find("\n    fun ", start + 20),
        src.find("\n    private fun ", start + 20),
    ]
    ends = [x for x in candidates if x >= 0]
    if not ends:
        raise SystemExit(f"v7.1 next function not found after {name}")
    end = min(ends)
    return src[:start] + replacement.rstrip() + "\n" + src[end:]

s = replace_private_function(s, "recordPrecisionScanFailure", r'''    private fun recordPrecisionScanFailure(message: String) {
        val detail = if (precisionLastDiagnostic.isBlank()) "診断情報なし" else precisionLastDiagnostic
        val full = message + "\n\n" + detail
        val prefs = getSharedPreferences("precision_diagnostics", MODE_PRIVATE)
        prefs.edit()
            .putString("last_failure", full)
            .putLong("last_failure_time", System.currentTimeMillis())
            .apply()

        if (!precisionFailureRecordSaved) {
            precisionFailureRecordSaved = true
            val precisionPointsForLog =
                if (precisionLogPoints.isNotEmpty()) precisionLogPoints.toList()
                else precisionCollector.snapshot()
            val markerDiagnostic = prefs.getString("last_marker", "") ?: ""
            val collectorDiagnostic =
                precisionCollector.diagnosticSummary() +
                    " quality=" + (precisionCurrentQuality?.summary() ?: "-")
            val ballForLog = ball
            val cupForLog = cup
            val meta = ScanFieldRecorder.CaptureMeta(
                appVersion = "Precision 7.1",
                trackingState = trackingStateText,
                viewportWidth = viewportW,
                viewportHeight = viewportH,
                cameraTranslation = latestCameraTranslation.copyOf(),
                cameraQuaternion = latestCameraQuaternion.copyOf(),
                ballScreenX = null,
                ballScreenY = null,
                cupScreenX = null,
                cupScreenY = null,
                arCoreDepthSupported = depthSupported
            )
            val identity = finalPrecisionRecordIdentity()
            val quality = precisionCurrentQuality

            val persistFailure: (Bitmap?) -> Unit = { failureBitmap ->
                Thread {
                    try {
                        if (identity != null) {
                            ScanFieldRecorder.saveFailureGrouped(
                                this,
                                precisionPointsForLog,
                                ballForLog,
                                cupForLog,
                                message,
                                detail,
                                markerDiagnostic,
                                collectorDiagnostic,
                                meta,
                                identity,
                                quality,
                                failureBitmap
                            )
                        } else {
                            ScanFieldRecorder.saveFailure(
                                this,
                                precisionPointsForLog,
                                ballForLog,
                                cupForLog,
                                message,
                                detail,
                                markerDiagnostic,
                                collectorDiagnostic,
                                meta,
                                failureBitmap
                            )
                        }
                    } catch (_: Throwable) {
                        // Field logging is best-effort and must never block play.
                    } finally {
                        failureBitmap?.recycle()
                    }
                }.start()
            }

            val captureW = gl.width
            val captureH = gl.height
            if (captureW > 0 && captureH > 0) {
                try {
                    val failureBitmap =
                        Bitmap.createBitmap(captureW, captureH, Bitmap.Config.ARGB_8888)
                    android.view.PixelCopy.request(
                        gl,
                        failureBitmap,
                        { result ->
                            if (result == android.view.PixelCopy.SUCCESS) {
                                persistFailure(failureBitmap)
                            } else {
                                failureBitmap.recycle()
                                persistFailure(null)
                            }
                        },
                        android.os.Handler(android.os.Looper.getMainLooper())
                    )
                } catch (_: Throwable) {
                    persistFailure(null)
                }
            } else {
                persistFailure(null)
            }
        }

        val advice = precisionCurrentQuality?.guidance?.firstOrNull()
        status.text = if (advice.isNullOrBlank()) {
            message + "（画像・診断を自動保存中）"
        } else {
            message + "\n" + advice + "（画像・診断を自動保存中）"
        }
        Toast.makeText(this, "再スキャンできます", Toast.LENGTH_SHORT).show()
        updatePrecisionRecordLabel()
    }
''')

r = replace_object_function(r, "saveFailureGrouped", r'''    fun saveFailureGrouped(
        context: Context,
        precisionPoints: List<PrecisionDepthPoint>,
        ball: Vec3?,
        cup: Vec3?,
        reason: String,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String,
        meta: CaptureMeta,
        identity: RecordIdentity,
        quality: PrecisionScanQuality?,
        failureBitmap: Bitmap? = null
    ): String {
        val folder = groupedFolder(identity, failed = true)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            failureBitmap?.let { bitmap ->
                writeDownload(context, rel, "camera.jpg", "image/jpeg") { out ->
                    if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) {
                        error("camera.jpg write failed")
                    }
                }
            }
            writeDownload(context, rel, "metadata.json", "application/json") { out ->
                out.bufferedWriter().use {
                    it.write(failureMetadataJson(ball, cup, reason, meta, precisionPoints.size))
                }
            }
            savePrecisionExtrasModern(
                context, folder, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            saveRecordExtrasModern(context, folder, identity, meta, quality)
            "Download/$ROOT/$folder"
        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            failureBitmap?.let { bitmap ->
                File(dir, "camera.jpg").outputStream().use { out ->
                    if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) {
                        error("camera.jpg write failed")
                    }
                }
            }
            File(dir, "metadata.json").writeText(
                failureMetadataJson(ball, cup, reason, meta, precisionPoints.size)
            )
            savePrecisionExtrasLegacy(
                dir, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            saveRecordExtrasLegacy(dir, identity, meta, quality)
            dir.absolutePath
        }
    }
''')

r = replace_object_function(r, "saveFailure", r'''    fun saveFailure(
        context: Context,
        precisionPoints: List<PrecisionDepthPoint>,
        ball: Vec3?,
        cup: Vec3?,
        reason: String,
        precisionDiagnostic: String,
        markerDiagnostic: String,
        collectorDiagnostic: String,
        meta: CaptureMeta,
        failureBitmap: Bitmap? = null
    ): String {
        val id = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val folder = "scan_${id}_FAILED"
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            failureBitmap?.let { bitmap ->
                writeDownload(context, rel, "camera.jpg", "image/jpeg") { out ->
                    if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) {
                        error("camera.jpg write failed")
                    }
                }
            }
            writeDownload(context, rel, "metadata.json", "application/json") { out ->
                out.bufferedWriter().use {
                    it.write(failureMetadataJson(ball, cup, reason, meta, precisionPoints.size))
                }
            }
            savePrecisionExtrasModern(
                context, folder, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            "Download/$ROOT/$folder"
        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            failureBitmap?.let { bitmap ->
                File(dir, "camera.jpg").outputStream().use { out ->
                    if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) {
                        error("camera.jpg write failed")
                    }
                }
            }
            File(dir, "metadata.json").writeText(
                failureMetadataJson(ball, cup, reason, meta, precisionPoints.size)
            )
            savePrecisionExtrasLegacy(
                dir, precisionPoints, precisionDiagnostic,
                markerDiagnostic, collectorDiagnostic
            )
            dir.absolutePath
        }
    }
''')

if 'Precision 7.0' not in s:
    raise SystemExit("v7.1 source version target missing")
s = s.replace('Precision 7.0', 'Precision 7.1')

if g.count('versionName = "7.0"') != 1 or g.count('versionCode = 700') != 1:
    raise SystemExit("v7.1 Gradle version target missing")
g = g.replace('versionName = "7.0"', 'versionName = "7.1"', 1)
g = g.replace('versionCode = 700', 'versionCode = 710', 1)

assert "android.view.PixelCopy.request(" in s
assert 'appVersion = "Precision 7.1"' in s
assert "failureBitmap: Bitmap? = null" in r
assert r.count('"camera.jpg"') >= 3
assert 'versionName = "7.1"' in g

main_path.write_text(s, encoding="utf-8")
recorder_path.write_text(r, encoding="utf-8")
gradle_path.write_text(g, encoding="utf-8")
print("Applied Precision v7.1 failed-scan camera capture")
