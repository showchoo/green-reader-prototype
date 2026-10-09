"""v9.2 opt-in Google Drive automatic backup of grouped scan sessions.

A complete local scan save triggers a debounced WorkManager sync. The saved
records are never deleted, and nothing uploads until user opts in via Google
Drive authorization in the Saved Data screen. All Drive writes use drive.file.
"""
from pathlib import Path
root=Path("app/src/main")
manager=root/"java/jp/example/greenreader/DataManagerActivity.kt"
rec=root/"java/jp/example/greenreader/field/ScanFieldRecorder.kt"
manifest=root/"AndroidManifest.xml"
gradle=Path("app/build.gradle.kts")
m=manager.read_text(encoding="utf8")
r=rec.read_text(encoding="utf8")
x=manifest.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def replace_once(source,old,new,context):
    n=source.count(old)
    if n!=1:raise SystemExit("v9.2 "+context+" expected once, got "+str(n))
    return source.replace(old,new,1)

m=replace_once(m,
'''import androidx.appcompat.app.AppCompatActivity''',
'''import androidx.appcompat.app.AppCompatActivity
import android.app.Activity
import jp.example.greenreader.field.DriveBackupScheduler
import jp.example.greenreader.field.DriveBackupWorker
import com.google.android.gms.auth.api.identity.Identity''',
"manager imports")
m=replace_once(m,
'''        private const val REQ_RECORDS_TREE = 9201''',
'''        private const val REQ_RECORDS_TREE = 9201
        private const val REQ_DRIVE_AUTH = 9302''',
"manager constants")
m=replace_once(m,
'''    private lateinit var empty: TextView''',
'''    private lateinit var empty: TextView
    private lateinit var driveBackupStatus: TextView
    private lateinit var driveBackupButton: Button''',
"manager fields")
m=replace_once(m,
'''        root.addView(top)

        root.addView(actionButton("全データ削除")''',
'''        root.addView(top)

        // Remote backup is explicitly opt-in; local scan saving is unchanged.
        driveBackupStatus = TextView(this).apply {
            setTextColor(Color.rgb(177, 243, 215))
            textSize = 12f
            setPadding(dp(4), dp(10), dp(4), dp(4))
        }
        root.addView(driveBackupStatus)
        driveBackupButton = actionButton("Google Drive自動保存を開始") {
            if (DriveBackupScheduler.isEnabled(this)) {
                DriveBackupScheduler.setEnabled(this, false)
                toast("Google Driveへの自動アップロードを停止しました")
                updateDriveBackupStatus()
            } else {
                askGoogleDriveConsent()
            }
        }
        root.addView(driveBackupButton, LinearLayout.LayoutParams(-1, dp(46)))
        updateDriveBackupStatus()

        root.addView(actionButton("全データ削除")''',
"manager UI")
helpers='''    private fun updateDriveBackupStatus() {
        if (!::driveBackupStatus.isInitialized || !::driveBackupButton.isInitialized) return
        val enabled = DriveBackupScheduler.isEnabled(this)
        val prefs = getSharedPreferences(DriveBackupScheduler.PREFS, MODE_PRIVATE)
        driveBackupButton.text =
            if (enabled) "Google Drive自動保存を停止" else "Google Drive自動保存を開始"
        driveBackupStatus.text =
            "保存先：Google Drive / ゴルフ場スキャンデータ" +
            "\\n状態：" + (if (enabled) "ON" else "OFF") +
            "\\n" + (prefs.getString("last_status", "") ?: "")
    }

    private fun askGoogleDriveConsent() {
        // Never start uploading on a request that has not actually been granted.
        driveBackupStatus.text = "Google Driveのアクセス許可を確認しています…"
        val client = Identity.getAuthorizationClient(this)
        client.authorize(DriveBackupWorker.authRequest())
            .addOnSuccessListener { result ->
                if (result.hasResolution()) {
                    try {
                        val intentSender = result.pendingIntent?.intentSender
                        if (intentSender == null) {
                            toast("Googleアカウントの許可画面を開けません")
                        } else {
                            @Suppress("DEPRECATION")
                            startIntentSenderForResult(
                                intentSender, REQ_DRIVE_AUTH, null, 0, 0, 0
                            )
                        }
                    } catch (e: Exception) {
                        toast("Google Drive連携を開始できません: " + e.javaClass.simpleName)
                        updateDriveBackupStatus()
                    }
                } else if (!result.accessToken.isNullOrBlank()) {
                    enableDriveBackup()
                } else {
                    toast("Google Driveのアクセス許可がありません")
                    updateDriveBackupStatus()
                }
            }
            .addOnFailureListener { error ->
                toast("Google Drive連携エラー: " + error.javaClass.simpleName)
                updateDriveBackupStatus()
            }
    }

    private fun onDriveAuthorizationResult(resultCode: Int, data: Intent?) {
        if (resultCode != Activity.RESULT_OK || data == null) {
            toast("Google Drive連携はキャンセルされました")
            updateDriveBackupStatus()
            return
        }
        try {
            val result = Identity.getAuthorizationClient(this)
                .getAuthorizationResultFromIntent(data)
            if (!result.accessToken.isNullOrBlank()) enableDriveBackup()
            else toast("Google Driveの許可が完了していません")
        } catch (e: Exception) {
            toast("Google Driveの認証を確認できません: " + e.javaClass.simpleName)
        }
        updateDriveBackupStatus()
    }

    private fun enableDriveBackup() {
        // Clear old-account fingerprints on re-enabling. If a different
        // Google account was selected, old account sync state must not carry.
        val wasEnabled = DriveBackupScheduler.isEnabled(this)
        if (!wasEnabled) {
            getSharedPreferences(DriveBackupScheduler.PREFS, MODE_PRIVATE)
                .edit().clear().apply()
        }
        DriveBackupScheduler.setEnabled(this, true)
        toast("自動保存を有効にしました。保存済みのセッションも同期対象です")
        updateDriveBackupStatus()
    }

'''
m=replace_once(m,'''    private fun refresh() {''',helpers+'''    private fun refresh() {''',"manager auth helpers")
m=replace_once(m,
'''        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_RECORDS_TREE || resultCode != RESULT_OK) return''',
'''        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_DRIVE_AUTH) {
            onDriveAuthorizationResult(resultCode, data)
            return
        }
        if (requestCode != REQ_RECORDS_TREE || resultCode != RESULT_OK) return''',
"merge Drive consent with existing SAF callback")

m=replace_once(m,'''        val folders = loadFolders()
        list.removeAllViews()''',
'''        val folders = loadFolders()
        updateDriveBackupStatus()
        list.removeAllViews()''',"manager refresh status")

# Two Android 10+ grouped save flows: success and failure. Schedule only
# after all local files are written and record_identity.json is emitted.
modern='''            saveRecordExtrasModern(context, folder, identity, meta, quality)
            "Download/$ROOT/$folder"'''
if r.count(modern)!=2:raise SystemExit("v9.2 modern grouped saves not exactly 2: "+str(r.count(modern)))
r=r.replace(modern,
'''            saveRecordExtrasModern(context, folder, identity, meta, quality)
            DriveBackupScheduler.onScanSaved(context)
            "Download/$ROOT/$folder"''')
legacy_success='''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            path'''
legacy_failed='''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            dir.absolutePath'''
r=replace_once(r,legacy_success,
'''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            DriveBackupScheduler.onScanSaved(context)
            path''',"legacy success callback")
r=replace_once(r,legacy_failed,
'''            saveRecordExtrasLegacy(dir, identity, meta, quality)
            DriveBackupScheduler.onScanSaved(context)
            dir.absolutePath''',"legacy failure callback")

x=replace_once(x,
'''    <uses-permission android:name="android.permission.CAMERA" />''',
'''    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />''',
"manifest internet network")
g=replace_once(g,
'''    implementation("com.google.ar:core:1.54.0")''',
'''    implementation("com.google.ar:core:1.54.0")
    implementation("com.google.android.gms:play-services-auth:21.5.0")
    implementation("androidx.work:work-runtime-ktx:2.11.2")''',
"google identity and WorkManager")
s=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").read_text(encoding="utf8")
if s.count("Precision 9.1") < 2:
    raise SystemExit("v9.2 expected v9.1 label")
s=s.replace("Precision 9.1", "Precision 9.2")
Path("app/src/main/java/jp/example/greenreader/MainActivity.kt").write_text(s,encoding="utf8")
g=replace_once(g,
'''versionCode = 910''','''versionCode = 920''',"version code")
g=replace_once(g,
'''versionName = "9.1"''','''versionName = "9.2"''',"version name")

for f,v in [(manager,m),(rec,r),(manifest,x),(gradle,g)]:
    f.write_text(v,encoding="utf8")
print("v9.2 opt-in Google Drive auth + after-save sync hooks installed")
