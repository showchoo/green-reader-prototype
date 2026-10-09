"""v9.3: make Drive consent failures diagnosable and use ActivityResult API.

A RESULT_CANCELED from Google Play Services does not prove that the user
pressed Cancel. OAuth SHA-1/package mismatch, test-user/consent policy,
Play Services errors, and real user cancellation can all need different
follow-up. This patch never assumes a successful authorization on cancel.
"""
from pathlib import Path

base=Path("app/src/main/java/jp/example/greenreader")
path=base/"DataManagerActivity.kt"
gpath=Path("app/build.gradle.kts")
main=base/"MainActivity.kt"
s=path.read_text(encoding="utf8")
g=gpath.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
def once(a,b,tag):
    global s
    n=s.count(a)
    if n!=1:raise SystemExit("v9.3 "+tag+" found "+str(n))
    s=s.replace(a,b,1)

once('''import com.google.android.gms.auth.api.identity.Identity''',
'''import com.google.android.gms.auth.api.identity.Identity
import com.google.android.gms.common.api.ApiException
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts''',"activity-result imports")
once('''        private const val REQ_DRIVE_AUTH = 9302
''','',"drop legacy request code")
once('''    private lateinit var driveBackupButton: Button''',
'''    private lateinit var driveBackupButton: Button

    private val driveAuthorizationLauncher =
        registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) {
            activityResult ->
            onDriveAuthorizationResult(activityResult.resultCode, activityResult.data)
        }''',"modern ActivityResult callback")

once('''        root.addView(driveBackupButton, LinearLayout.LayoutParams(-1, dp(46)))
        updateDriveBackupStatus()''',
'''        root.addView(driveBackupButton, LinearLayout.LayoutParams(-1, dp(46)))
        root.addView(actionButton("Drive連携の診断をコピー") {
            val prefs = getSharedPreferences(DriveBackupScheduler.PREFS, MODE_PRIVATE)
            val diagnostic = prefs.getString("last_auth_diagnostic", "まだ認証記録がありません") ?: ""
            val cm = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
            cm.setPrimaryClip(android.content.ClipData.newPlainText("Drive Auth", diagnostic))
            toast("診断情報をコピーしました（トークンは含みません）")
        }, LinearLayout.LayoutParams(-1, dp(42)))
        updateDriveBackupStatus()''',"diagnostic copy button")

once('''            "\\n" + (prefs.getString("last_status", "") ?: "")''',
'''            "\\n" + (prefs.getString("last_status", "") ?: "") +
            "\\n認証：" + (prefs.getString("last_auth_diagnostic", "未連携") ?: "")''',"show diagnostic")

old='''                        val intentSender = result.pendingIntent?.intentSender
                        if (intentSender == null) {
                            toast("Googleアカウントの許可画面を開けません")
                        } else {
                            @Suppress("DEPRECATION")
                            startIntentSenderForResult(
                                intentSender, REQ_DRIVE_AUTH, null, 0, 0, 0
                            )
                        }'''
new='''                        val pendingIntent = result.pendingIntent
                        if (pendingIntent == null) {
                            saveDriveAuthDiagnostic("OAuth pendingIntent missing")
                            toast("Googleアカウントの許可画面を開けません")
                        } else {
                            driveAuthorizationLauncher.launch(
                                IntentSenderRequest.Builder(pendingIntent.intentSender).build()
                            )
                        }'''
once(old,new,"use ActivityResult launcher")
once('''                        toast("Google Drive連携を開始できません: " + e.javaClass.simpleName)
                        updateDriveBackupStatus()''',
'''                        saveDriveAuthDiagnostic(
                            "OAuth intent launch exception=" + e.javaClass.simpleName +
                            ", status=" + (e as? ApiException)?.statusCode
                        )
                        toast("Google Driveの認証画面を開けません。診断を確認してください")
                        updateDriveBackupStatus()''',"intent-launch diagnostic")
once('''                    toast("Google Driveのアクセス許可がありません")
                    updateDriveBackupStatus()''',
'''                    saveDriveAuthDiagnostic("OAuth result has neither resolution nor token")
                    toast("Google Driveのアクセス許可がありません")
                    updateDriveBackupStatus()''',"missing token diagnostic")
once('''                toast("Google Drive連携エラー: " + error.javaClass.simpleName)
                updateDriveBackupStatus()''',
'''                saveDriveAuthDiagnostic(
                    "OAuth authorize failed: " + error.javaClass.simpleName +
                    ", status=" + (error as? ApiException)?.statusCode
                )
                toast("Google Driveの認証エラーです。診断コードを確認してください")
                updateDriveBackupStatus()''',"task failure diagnostic")

old='''    private fun onDriveAuthorizationResult(resultCode: Int, data: Intent?) {
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

'''
new='''    private fun saveDriveAuthDiagnostic(detail: String) {
        // Never save authorization tokens, account addresses or full intents.
        val sanitized = detail.take(350)
        getSharedPreferences(DriveBackupScheduler.PREFS, MODE_PRIVATE)
            .edit().putString("last_auth_diagnostic", sanitized).apply()
    }

    private fun onDriveAuthorizationResult(resultCode: Int, data: Intent?) {
        if (resultCode != Activity.RESULT_OK) {
            val apiStatus = if (data != null) {
                try {
                    Identity.getAuthorizationClient(this)
                        .getAuthorizationResultFromIntent(data)
                    "unexpected success token"
                } catch (e: ApiException) {
                    "Google status=" + e.statusCode
                } catch (e: Exception) {
                    "Google exception=" + e.javaClass.simpleName
                }
            } else "no result data"
            saveDriveAuthDiagnostic(
                "OAuth incomplete: resultCode=" + resultCode + ", " + apiStatus +
                ". Check Google Cloud Android OAuth package/SHA-1, test users, consent screen."
            )
            toast("Drive連携が完了していません。『Drive連携の診断をコピー』を押してください")
            updateDriveBackupStatus()
            return
        }
        if (data == null) {
            saveDriveAuthDiagnostic("OAuth RESULT_OK but no intent data")
            toast("Google認証の結果データがありません。診断を確認してください")
            updateDriveBackupStatus()
            return
        }
        try {
            val result = Identity.getAuthorizationClient(this)
                .getAuthorizationResultFromIntent(data)
            if (!result.accessToken.isNullOrBlank()) {
                enableDriveBackup()
                saveDriveAuthDiagnostic("OAuth authorized successfully; no token stored")
            } else {
                saveDriveAuthDiagnostic("OAuth RESULT_OK, accessToken is absent")
                toast("Google Driveの許可が完了していません")
            }
        } catch (e: Exception) {
            saveDriveAuthDiagnostic(
                "OAuth result failed: " + e.javaClass.simpleName +
                ", Google status=" + (e as? ApiException)?.statusCode
            )
            toast("Google Driveの認証に失敗しました。診断を確認してください")
        }
        updateDriveBackupStatus()
    }

'''
once(old,new,"accurate outcome and diagnostic")
once('''        if (requestCode == REQ_DRIVE_AUTH) {
            onDriveAuthorizationResult(resultCode, data)
            return
        }
''','',"remove duplicate callback")
if s.count('override fun onActivityResult(')!=1:raise SystemExit("v9.3 SAF callback lost")
# Preserve existing diagnostic and recent consent outcome even when enabling.
once('''        if (!wasEnabled) {
            getSharedPreferences(DriveBackupScheduler.PREFS, MODE_PRIVATE)
                .edit().clear().apply()
        }''',
'''        if (!wasEnabled) {
            getSharedPreferences(DriveBackupScheduler.PREFS, MODE_PRIVATE)
                .edit().remove("last_status").apply()
        }''',"preserve OAuth diagnostic")
if g.count('versionName = "9.2"')!=1 or g.count('versionCode = 920')!=1:raise SystemExit("version mismatch")
g=g.replace('versionName = "9.2"','versionName = "9.3"').replace('versionCode = 920','versionCode = 930')
if m.count('Precision 9.2')<2:raise SystemExit("no v9.2 app labels")
m=m.replace('Precision 9.2','Precision 9.3')
path.write_text(s,encoding="utf8")
gpath.write_text(g,encoding="utf8")
main.write_text(m,encoding="utf8")
print("v9.3: modern consent result handling + actionable, token-free diagnostic")
