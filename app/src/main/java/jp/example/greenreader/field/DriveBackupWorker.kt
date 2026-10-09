package jp.example.greenreader.field

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.google.android.gms.auth.api.identity.AuthorizationRequest
import com.google.android.gms.auth.api.identity.Identity
import com.google.android.gms.common.api.Scope
import com.google.android.gms.tasks.Tasks
import java.util.concurrent.TimeUnit

/**
 * WorkManager retries network failures after user opt-in. It cannot display
 * an OAuth consent UI in the background; a new consent is requested in the
 * Saved Data screen instead when Google demands interaction.
 */
class DriveBackupWorker(context: Context, params: WorkerParameters): Worker(context, params) {
    companion object {
        const val DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"
        fun authRequest(): AuthorizationRequest =
            AuthorizationRequest.builder()
                .setRequestedScopes(listOf(Scope(DRIVE_FILE))).build()
    }

    private val prefs = applicationContext.getSharedPreferences(
        DriveBackupScheduler.PREFS, Context.MODE_PRIVATE
    )
    private fun status(s: String) {
        prefs.edit().putString("last_status", s)
            .putLong("status_time", System.currentTimeMillis()).apply()
    }

    override fun doWork(): Result {
        if (!DriveBackupScheduler.isEnabled(applicationContext)) return Result.success()
        status("Google Driveへ同期を確認中…")
        return try {
            val auth = Tasks.await(
                Identity.getAuthorizationClient(applicationContext).authorize(authRequest()),
                30, TimeUnit.SECONDS
            )
            if (auth.hasResolution() || auth.accessToken.isNullOrBlank()) {
                status("Google Drive再認証が必要です。「保存データ」から連携を確認してください")
                return Result.failure()
            }
            val token = auth.accessToken!!
            val sessions = DriveBackupArchive.sessions(applicationContext)
            if (sessions.isEmpty()) {
                status("同期対象のセッションがまだありません")
                return Result.success()
            }
            val changed = sessions.filter {
                prefs.getString("synced_" + it.name, "") != it.fingerprint()
            }
            if (changed.isEmpty()) {
                status("すべて同期済み（" + sessions.size + "セッション）")
                return Result.success()
            }
            val client = DriveBackupUploader(token)
            val folder = client.ensureFolder()
            var sent = 0
            // Limit each worker to avoid Android's 10-minute background limit.
            for (session in changed.take(2)) {
                if (isStopped) return Result.retry()
                val zip = DriveBackupArchive.zip(applicationContext, session)
                try {
                    client.upsertSession(folder, session.zipName, zip)
                    prefs.edit()
                        .putString("synced_" + session.name, session.fingerprint())
                        .putLong("last_uploaded_at", System.currentTimeMillis())
                        .apply()
                    sent++
                } finally {
                    zip.delete()
                }
            }
            status("ゴルフ場スキャンデータ：同期完了 " + sent +
                "件（未送信残り " + (changed.size - sent) + "件）")
            if (changed.size > sent) Result.retry() else Result.success()
        } catch (e: DriveBackupUploader.ApiException) {
            if (e.status == 401 || e.status == 403) {
                status("Google Driveの許可を確認してください（HTTP " + e.status + "）")
                Result.failure()
            } else {
                status("通信エラーで同期待機中（HTTP " + e.status + "）")
                Result.retry()
            }
        } catch (e: Exception) {
            // Never delete source records and never claim a failed sync worked.
            status("同期保留中: " + e.javaClass.simpleName)
            Result.retry()
        }
    }
}
