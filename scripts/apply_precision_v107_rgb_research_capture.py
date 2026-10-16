"""Research-only v10.7: opt-in, CPU-camera RGB/pose/IMU bursts saved with scan.

Runs only AFTER v10.6 has generated the known-safe code. Does not alter
Depth unprojection, surface geometry, analysis, confidence or aim gates.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
main=root/"MainActivity.kt"
record=root/"field/ScanFieldRecorder.kt"
gradle=Path("app/build.gradle.kts")
m=main.read_text(encoding="utf-8")
r=record.read_text(encoding="utf-8")
g=gradle.read_text(encoding="utf-8")

def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise RuntimeError(f"v10.7 RGB {label}: expected once, found {n}")
    return s.replace(old,new,1)

m=one(m,
'''import jp.example.greenreader.field.ScanFieldRecorder''',
'''import jp.example.greenreader.field.ScanFieldRecorder
import jp.example.greenreader.field.PrecisionRgbBurstRecorder''',"research recorder import")

m=one(m,
'''    private val precisionCollector = PrecisionDepthCollector()''',
'''    private val precisionCollector = PrecisionDepthCollector()

    private fun rgbResearchEnabled(): Boolean =
        getSharedPreferences("rgb_multiview_research", MODE_PRIVATE)
            .getBoolean("enabled",false)

    private fun setRgbResearchEnabled(enabled: Boolean) {
        getSharedPreferences("rgb_multiview_research", MODE_PRIVATE)
            .edit().putBoolean("enabled",enabled).apply()
    }''',
"opt-in persisted state, default off")

m=one(m,
'''        expandedMenu.addView(row6)''',
'''        expandedMenu.addView(row6)

        // Research opt-in: these are actual CPU camera images, NOT a GL
        // screenshot. Never silently upload a sequence without user consent.
        val rgbRow=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
        lateinit var rgbToggle: Button
        rgbToggle=button("研究RGB連続記録: " +
            (if(rgbResearchEnabled()) "ON" else "OFF")) {
            if (rgbResearchEnabled()) {
                setRgbResearchEnabled(false)
                rgbToggle.text="研究RGB連続記録: OFF"
                Toast.makeText(this,"次のスキャンからRGB記録を停止します",Toast.LENGTH_SHORT).show()
            } else {
                android.app.AlertDialog.Builder(this)
                    .setTitle("研究用RGB連続記録")
                    .setMessage(
                        "スキャン中、最大96枚のカラー画像と姿勢・時刻・" +
                        "加速度／ジャイロ情報を保存します。既存のGoogle Drive自動保存が" +
                        "有効なら、この研究データもご自身のDriveへアップロードされます。" +
                        "人物や私物が映り込まない床面でのみ使用してください。" +
                        "精密な傾斜計測を保証する機能ではありません。"
                    )
                    .setNegativeButton("キャンセル",null)
                    .setPositiveButton("研究記録を有効化") { _, _ ->
                        setRgbResearchEnabled(true)
                        rgbToggle.text="研究RGB連続記録: ON"
                        Toast.makeText(this,"次のスキャンからRGB連続記録します",Toast.LENGTH_LONG).show()
                    }.show()
            }
        }
        rgbRow.addView(rgbToggle,LinearLayout.LayoutParams(-1,dp(42)))
        expandedMenu.addView(rgbRow)''',
"explicit opt-in UI in collapsible menu")

m=one(m,
'''        precisionFailureRecordSaved = false
        scanning = true''',
'''        precisionFailureRecordSaved = false
        if (rgbResearchEnabled()) {
            precisionCurrentRecord?.let {
                // Exactly the same Scan identity will be used in the saver.
                PrecisionRgbBurstRecorder.begin(this,it)
            }
        }
        scanning = true''',
"start research sequence under scan identity")

m=one(m,
'''                if (referenceAnchor?.trackingState == TrackingState.TRACKING) {
                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)''',
'''                if (referenceAnchor?.trackingState == TrackingState.TRACKING) {
                    // CPU image and ARCore camera pose are from the SAME Frame.
                    // Cannot access the CPU image after moving to a newer Frame.
                    if (rgbResearchEnabled()) {
                        PrecisionRgbBurstRecorder.capture(
                            f, referenceAnchor.pose,
                            cupAnchor?.takeIf { it.trackingState == TrackingState.TRACKING }?.pose
                        )
                    }
                    collector.integrate(f, referenceAnchor.pose, pixelStrideStep = 4)''',
"capture before depth processing in single ARCore GL frame")

# Capture files are written before the worker is scheduled, so complete ZIPs
# contain the RGB sequence. Folder depth stays Session/Putt/Scan (3 levels).
method=r'''    private fun saveRgbResearchModern(
        context: Context,
        folder: String,
        identity: RecordIdentity
    ) {
        val rel=Environment.DIRECTORY_DOWNLOADS + "/$ROOT/$folder"
        PrecisionRgbBurstRecorder.finishAndWrite(context,identity) { name,mime,file ->
            writeDownload(context,rel,name,mime) { out ->
                file.inputStream().use { it.copyTo(out,64*1024) }
            }
        }
    }

    private fun saveRgbResearchLegacy(dir: File,identity: RecordIdentity,context: Context) {
        PrecisionRgbBurstRecorder.finishAndWrite(context,identity) { name,_,file ->
            file.copyTo(File(dir,name),overwrite=true)
        }
    }

'''
r=one(r,
'''    private fun saveRecordExtrasModern(''',
method+'''    private fun saveRecordExtrasModern(''',
"research archive save helpers")

oldModern='''            saveRecordExtrasModern(context, folder, identity, meta, quality)
            DriveBackupScheduler.onScanSaved(context)'''
if r.count(oldModern)!=2:
    raise RuntimeError("v10.7 expected 2 grouped modern save sites, got "+str(r.count(oldModern)))
r=r.replace(oldModern,
'''            saveRecordExtrasModern(context, folder, identity, meta, quality)
            saveRgbResearchModern(context,folder,identity)
            DriveBackupScheduler.onScanSaved(context)''')

r=one(r,
'''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            DriveBackupScheduler.onScanSaved(context)
            path''',
'''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            saveRgbResearchLegacy(dir,identity,context)
            DriveBackupScheduler.onScanSaved(context)
            path''',
"legacy success")
r=one(r,
'''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            DriveBackupScheduler.onScanSaved(context)
            dir.absolutePath''',
'''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            saveRgbResearchLegacy(dir,identity,context)
            DriveBackupScheduler.onScanSaved(context)
            dir.absolutePath''',
"legacy failure")

if m.count("Precision 10.6")<2: raise RuntimeError("expected generated v10.6 labels")
m=m.replace("Precision 10.6","Precision 10.7 RGB研究")
g=one(g,'versionName = "10.6"','versionName = "10.7-rgb-research"',"version name")
g=one(g,'versionCode = 1060','versionCode = 1070',"version code")

assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'PrecisionDepthFreshnessPolicy.evaluate(' in (root/"precision/PrecisionDepthCollector.kt").read_text()
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'DriveBackupScheduler.onScanSaved(context)' in r
assert 'button("次のパット")' in m and 'button("結果入力")' in m
assert r.index("saveRgbResearchModern(context,folder,identity)") < r.index('DriveBackupScheduler.onScanSaved(context)')
assert (root/"field/PrecisionRgbBurstRecorder.kt").exists()
assert (root/"precision/PrecisionYuv420Nv21.kt").exists()
main.write_text(m,encoding="utf-8")
record.write_text(r,encoding="utf-8")
gradle.write_text(g,encoding="utf-8")
print("v10.7 RGB-research: opt-in CPU RGB sequences, timestamp/camera/IMU aligned per Frame; safe geometry unchanged")
