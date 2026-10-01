"""Precision v7.1: field-test recording improvements without changing measurement math."""
from pathlib import Path

main = Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s = main.read_text(encoding="utf-8")
rec = Path("app/src/main/java/jp/example/greenreader/field/ScanFieldRecorder.kt")
r = rec.read_text(encoding="utf-8")

def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"v7.1 {label}: expected 1 target, got {count}")
    return text.replace(old, new, 1)

r = once(r,
"""        val scanIndex: Int,
        val scanStartedAtEpochMs: Long,
""",
"""        val scanIndex: Int,
        val holeNumber: Int,
        val scanStartedAtEpochMs: Long,
""",
"RecordIdentity hole number")

r = once(r,
'''  "scan_index": ${identity.scanIndex},
  "scan_started_at_epoch_ms": ${identity.scanStartedAtEpochMs},
''',
'''  "scan_index": ${identity.scanIndex},
  "hole_number": ${identity.holeNumber},
  "scan_started_at_epoch_ms": ${identity.scanStartedAtEpochMs},
''',
"record identity JSON hole number")

fg_start = r.index("    fun saveFailureGrouped(")
fg_end = r.index("\n    private fun groupedFolder", fg_start)
fg = r[fg_start:fg_end]

fg = once(fg,
"""        identity: RecordIdentity,
        quality: PrecisionScanQuality?
    ): String {
""",
"""        identity: RecordIdentity,
        quality: PrecisionScanQuality?,
        bitmap: Bitmap? = null
    ): String {
""",
"failure grouped bitmap parameter")

fg = once(fg,
"""        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            writeDownload(context, rel, "metadata.json", "application/json") { out ->
""",
"""        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            bitmap?.let { failureBitmap ->
                writeDownload(context, rel, "camera.jpg", "image/jpeg") { out ->
                    if (!failureBitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)) error("camera.jpg write failed")
                }
            }
            writeDownload(context, rel, "metadata.json", "application/json") { out ->
""",
"failure grouped modern camera image")

fg = once(fg,
"""        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            File(dir, "metadata.json").writeText(
""",
"""        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            bitmap?.let { failureBitmap ->
                File(dir, "camera.jpg").outputStream().use {
                    failureBitmap.compress(Bitmap.CompressFormat.JPEG, 92, it)
                }
            }
            File(dir, "metadata.json").writeText(
""",
"failure grouped legacy camera image")

r = r[:fg_start] + fg + r[fg_end:]

insert_before = "    private fun groupedFolder(identity: RecordIdentity, failed: Boolean): String {\n"
if insert_before not in r:
    raise SystemExit("v7.1 result recorder insertion point missing")
result_fn = r'''    fun savePuttResult(
        context: Context,
        identity: RecordIdentity,
        resultCode: String
    ): String {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val session = identity.sessionId.replace(Regex("[^A-Za-z0-9_-]"), "_")
        val putt = String.format(Locale.US, "Putt_%03d", identity.puttId)
        val folder = "Session_$session/$putt"
        val fileName = "putt_result_$stamp.json"
        val json = """{
  "schema_version": 1,
  "session_id": "${escape(identity.sessionId)}",
  "putt_id": ${identity.puttId},
  "hole_number": ${identity.holeNumber},
  "last_scan_index": ${identity.scanIndex},
  "recorded_at_epoch_ms": ${System.currentTimeMillis()},
  "result": "${escape(resultCode)}",
  "manufacturer": "${escape(Build.MANUFACTURER)}",
  "model": "${escape(Build.MODEL)}"
}
"""
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel = Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            writeDownload(context, rel, fileName, "application/json") { out ->
                out.bufferedWriter().use { it.write(json) }
            }
            "Download/$ROOT/$folder/$fileName"
        } else {
            val dir = File(context.getExternalFilesDir(null), "$ROOT/$folder").apply { mkdirs() }
            File(dir, fileName).writeText(json)
            File(dir, fileName).absolutePath
        }
    }

'''
r = r.replace(insert_before, result_fn + insert_before, 1)

s = once(s,
"""    private var precisionPuttId = 1
    private var precisionScanIndex = 0
""",
"""    private var precisionPuttId = 1
    private var precisionHoleNumber = 1
    private var precisionScanIndex = 0
""",
"hole state")

s = once(s,
"""            puttId = precisionPuttId,
            scanIndex = precisionScanIndex,
            scanStartedAtEpochMs = recordStartedAt,
""",
"""            puttId = precisionPuttId,
            scanIndex = precisionScanIndex,
            holeNumber = precisionHoleNumber,
            scanStartedAtEpochMs = recordStartedAt,
""",
"identity construction hole")

old_row = '''        val row6 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row6.addView(
            button("次のパット") { beginNextPrecisionPutt() },
            LinearLayout.LayoutParams(0, dp(42), 1f)
        )
        expandedMenu.addView(row6)
'''
new_row = '''        val row6 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row6.addView(button("次のパット") { beginNextPrecisionPutt() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        row6.addView(button("次のホール") { beginNextPrecisionHole() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        row6.addView(button("結果入力") { showPrecisionPuttResultDialog() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        expandedMenu.addView(row6)
'''
s = once(s, old_row, new_row, "field result buttons")

s = once(s,
'''            "  /  PUTT " + String.format("%03d", precisionPuttId) +
                "  /  SCAN " + String.format("%02d", precisionScanIndex) +
''',
'''            "  /  HOLE " + String.format("%02d", precisionHoleNumber) +
                "  /  PUTT " + String.format("%03d", precisionPuttId) +
                "  /  SCAN " + String.format("%02d", precisionScanIndex) +
''',
"record label hole")

helper_marker = "    private fun updatePrecisionRecordLabel() {\n"
if helper_marker not in s:
    raise SystemExit("v7.1 helper insertion point missing")
helpers = r'''    private fun beginNextPrecisionHole() {
        if (scanning) {
            Toast.makeText(this, "測定終了後に次のホールへ進んでください", Toast.LENGTH_SHORT).show()
            return
        }
        precisionHoleNumber += 1
        beginNextPrecisionPutt()
        status.text = "Hole " + String.format("%02d", precisionHoleNumber) +
            " / Putt " + String.format("%03d", precisionPuttId) +
            "：ボールをタップしてください"
    }

    private fun showPrecisionPuttResultDialog() {
        val identity = finalPrecisionRecordIdentity()
        if (identity == null) {
            Toast.makeText(this, "先にこのパットを測定してください", Toast.LENGTH_SHORT).show()
            return
        }
        val labels = arrayOf(
            "IN",
            "左ショート", "左・距離OK", "左オーバー",
            "中央ショート", "中央オーバー",
            "右ショート", "右・距離OK", "右オーバー"
        )
        val codes = arrayOf(
            "IN",
            "LEFT_SHORT", "LEFT_OK", "LEFT_LONG",
            "CENTER_SHORT", "CENTER_LONG",
            "RIGHT_SHORT", "RIGHT_OK", "RIGHT_LONG"
        )
        android.app.AlertDialog.Builder(this)
            .setTitle("実際のパット結果")
            .setItems(labels) { _, which ->
                val code = codes[which]
                Thread {
                    try {
                        ScanFieldRecorder.savePuttResult(this, identity, code)
                        runOnUiThread {
                            Toast.makeText(this, "結果を保存しました: " + labels[which], Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Throwable) {
                        runOnUiThread {
                            Toast.makeText(this, "結果保存に失敗: " + (e.message ?: "不明"), Toast.LENGTH_SHORT).show()
                        }
                    }
                }.start()
            }
            .setNegativeButton("キャンセル", null)
            .show()
    }

'''
s = s.replace(helper_marker, helpers + helper_marker, 1)

old_failure_thread = '''            val identity = finalPrecisionRecordIdentity()
            val quality = precisionCurrentQuality
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
                            quality
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
                            meta
                        )
                    }
                } catch (_: Throwable) {
                    // Field logging must never block another measurement.
                }
            }.start()
'''
new_failure_thread = '''            val identity = finalPrecisionRecordIdentity()
            val quality = precisionCurrentQuality
            val saveFailurePackage: (Bitmap?) -> Unit = { failureBitmap ->
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
                                bitmap = failureBitmap
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
                                meta
                            )
                        }
                    } catch (_: Throwable) {
                    } finally {
                        failureBitmap?.recycle()
                    }
                }.start()
            }
            try {
                gl.queueEvent {
                    val failureBitmap = try { captureGlFrame(viewportW, viewportH) } catch (_: Throwable) { null }
                    saveFailurePackage(failureBitmap)
                }
            } catch (_: Throwable) {
                saveFailurePackage(null)
            }
'''
s = once(s, old_failure_thread, new_failure_thread, "failure screenshot logging")

s = s.replace("Precision 7.0", "Precision 7.1")

gpath = Path("app/build.gradle.kts")
g = gpath.read_text(encoding="utf-8")
if g.count('versionName = "7.0"') != 1 or g.count('versionCode = 700') != 1:
    raise SystemExit("v7.1 Gradle version target missing")
g = g.replace('versionName = "7.0"', 'versionName = "7.1"', 1)
g = g.replace('versionCode = 700', 'versionCode = 710', 1)

assert "holeNumber = precisionHoleNumber" in s
assert 'button("結果入力")' in s
assert "ScanFieldRecorder.savePuttResult" in s
assert "bitmap = failureBitmap" in s
assert '"hole_number": ${identity.holeNumber}' in r
assert "putt_result_$stamp.json" in r

main.write_text(s, encoding="utf-8")
rec.write_text(r, encoding="utf-8")
gpath.write_text(g, encoding="utf-8")
print("Applied Precision v7.1 field-test recording improvements")
