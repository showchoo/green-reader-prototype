package jp.example.greenreader.field

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/**
 * Explicit opt-in: no camera images or depth points are ever sent without
 * the user's own Google Drive authorization and the enabled switch.
 */
object DriveBackupScheduler {
    const val FOLDER_NAME = "ゴルフ場スキャンデータ"
    const val PREFS = "green_reader_drive_backup"
    private const val IMMEDIATE = "green-reader-drive-backup"
    private const val PERIODIC = "green-reader-drive-backup-periodic"

    fun isEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean("enabled", false)

    fun setEnabled(context: Context, enabled: Boolean) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.edit().putBoolean("enabled", enabled).apply()
        if (enabled) {
            enqueue(context)
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build()
            val request = PeriodicWorkRequestBuilder<DriveBackupWorker>(
                6, TimeUnit.HOURS
            ).setConstraints(constraints).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC, ExistingPeriodicWorkPolicy.KEEP, request
            )
        } else {
            WorkManager.getInstance(context).cancelUniqueWork(IMMEDIATE)
            WorkManager.getInstance(context).cancelUniqueWork(PERIODIC)
        }
    }

    /** Called only AFTER the completed local save. Network errors never roll
     * back the local files, and incomplete in-progress scans are not uploaded.
     */
    fun onScanSaved(context: Context) {
        if (isEnabled(context)) enqueue(context)
    }

    fun enqueue(context: Context) {
        if (!isEnabled(context)) return
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED).build()
        val request = OneTimeWorkRequestBuilder<DriveBackupWorker>()
            .setInitialDelay(15, TimeUnit.SECONDS)
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
            .build()
        // Each newly completed scan replaces a pending 15s debounce window.
        // The periodic sweep catches scans written while an upload is running.
        WorkManager.getInstance(context).enqueueUniqueWork(
            IMMEDIATE, ExistingWorkPolicy.REPLACE, request
        )
    }
}
