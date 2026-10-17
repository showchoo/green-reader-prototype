"""v10.9 research: no-scan read-only Camera2 DEPTH16 capabilities + opt-in Drive report."""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
rec=root/"field/ScanFieldRecorder.kt"
gradle=Path("app/build.gradle.kts")
m=main.read_text(encoding="utf-8")
r=rec.read_text(encoding="utf-8")
g=gradle.read_text(encoding="utf-8")

def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f"v10.9 {label}: expected 1, got {n}")
    return s.replace(old,new,1)

m=one(m,
'''import jp.example.greenreader.field.PrecisionRgbBurstRecorder''',
'''import jp.example.greenreader.field.PrecisionRgbBurstRecorder
import jp.example.greenreader.precision.PrecisionCamera2DepthProbe''',
"read-only probe import")

m=one(m,
'''        expandedMenu.addView(rgbRow)''',
'''        expandedMenu.addView(rgbRow)

        // Read Camera2 characteristics only; never open a competing camera.
        val camera2Row=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
        camera2Row.addView(button("ToF / Camera2深度を確認・保存") {
            if (scanning) {
                Toast.makeText(this,
                    "スキャン終了後に確認してください",Toast.LENGTH_SHORT).show()
            } else {
                status.text="端末のCamera2深度対応を調査しています…"
                Thread {
                    try {
                        val report=PrecisionCamera2DepthProbe.probe(this)
                        val saved=ScanFieldRecorder.saveHardwareProbe(this,report.json)
                        val summary=when(report.state) {
                            "PUBLIC_CAMERA2_DEPTH16" ->
                                "DEPTH16画像形式を公開するカメラを確認しました。" +
                                "ただしToFセンサー同一性と傾斜精度は未検証です。"
                            "NO_PUBLIC_CAMERA2_DEPTH16" ->
                                "公開Camera2 APIからDEPTH16形式を確認できませんでした。" +
                                "物理ToFの不存在を意味するものではありません。"
                            else ->
                                "一部のカメラ情報を取得できず、DEPTH16対応は判定保留です。"
                        }
                        runOnUiThread {
                            status.text="Camera2機能の確認データを保存しました"
                            android.app.AlertDialog.Builder(this)
                                .setTitle("Camera2深度機能の確認結果")
                                .setMessage(summary + "\\n\\n公開DEPTH16候補：" +
                                    report.depth16CameraCount + "台" +
                                    "\\n確認できたカメラ：" + report.probedCameraCount +
                                    "台" +
                                    "\\nエラー：" + report.errorCount + "件" +
                                    "\\n\\n保存先：" + saved +
                                    "\\n既存Google Drive自動保存がONなら同期します。")
                                .setPositiveButton("OK",null).show()
                        }
                    } catch (e:Exception) {
                        runOnUiThread {
                            status.text="Camera2確認エラー：" +
                                (e.message ?: e.javaClass.simpleName)
                        }
                    }
                }.start()
            }
        },LinearLayout.LayoutParams(-1,dp(42)))
        expandedMenu.addView(camera2Row)''',
"one-tap capability UI")

helper=r'''    /**
     * A hardware-only Session. Existing DriveBackupArchive still sees a
     * Session/Putt/Scan folder with final record_identity.json marker.
     * No ARCore scan or photo is generated.
     */
    fun saveHardwareProbe(context: Context, probeJson: String): String {
        val stamp=SimpleDateFormat("yyyyMMdd_HHmmss_SSS",Locale.US).format(Date())
        val sessionName="Session_HW_" + stamp
        val folder="$sessionName/Putt_000/Scan_01_CAMERA2"
        val identity = """{
  "schema_version": 4,
  "session_id": "HW_$stamp",
  "record_kind": "camera2_read_only_probe",
  "putt_id": 0,
  "scan_index": 1,
  "hole_number": 0,
  "app_version": "Precision 10.9 Camera2研究",
  "recorded_at_epoch_ms": __EPOCH_INTERPOLATION__,
  "accuracy_certified": false
}
"""
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rel=Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
            // Completion marker last; Drive archive excludes unfinished saves.
            writeDownload(context,rel,"camera2_capabilities.json","application/json") { out ->
                out.bufferedWriter().use { it.write(probeJson) }
            }
            writeDownload(context,rel,"record_identity.json","application/json") { out ->
                out.bufferedWriter().use { it.write(identity) }
            }
        } else {
            val dir=File(context.getExternalFilesDir(null),"$ROOT/$folder")
                .apply { mkdirs() }
            File(dir,"camera2_capabilities.json").writeText(probeJson)
            File(dir,"record_identity.json").writeText(identity)
        }
        DriveBackupScheduler.onScanSaved(context)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
            "Download/$ROOT/$folder" else "$ROOT/$folder"
    }

'''.replace('__EPOCH_INTERPOLATION__','$'+'{System.currentTimeMillis()}')

r=one(r,
'''    private fun groupedFolder(identity: RecordIdentity, failed: Boolean): String {''',
helper+'''    private fun groupedFolder(identity: RecordIdentity, failed: Boolean): String {''',
"own Drive archival session")

if m.count("Precision 10.8 RGB研究")<2:
    raise RuntimeError("v10.9 requires generated v10.8")
m=m.replace("Precision 10.8 RGB研究","Precision 10.9 Camera2研究")
g=one(g,'versionName = "10.8-rgb-jpeg-repair"',
      'versionName = "10.9-camera2-probe"',"version")
g=one(g,'versionCode = 1080','versionCode = 1090',"version code")
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionRgbBurstRecorder.capture(' in m
assert 'PrecisionAnchoredGroundSelector.select(' in (
    root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert r.count('DriveBackupScheduler.onScanSaved(context)') >= 5
main.write_text(m,encoding="utf-8")
rec.write_text(r,encoding="utf-8")
gradle.write_text(g,encoding="utf-8")
print("v10.9: Camera2 capabilities read-only button + independent Drive report")
