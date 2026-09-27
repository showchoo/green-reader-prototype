package jp.example.greenreader

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.util.Base64
import android.widget.EditText
import com.google.android.gms.auth.api.identity.AuthorizationRequest
import com.google.android.gms.auth.api.identity.Identity
import com.google.android.gms.common.api.Scope
import com.google.android.gms.common.api.ApiException
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class GmailAutoReporter(
    private val activity: Activity,
    private val onStatus: (String) -> Unit
) {
    companion object {
        const val REQUEST_CODE = 9187
        private const val GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
        private const val PREFS = "gmail_auto_reporter"
        private const val KEY_RECIPIENT = "recipient"
        private const val KEY_ENTRIES = "entries"
    }

    private val prefs = activity.getSharedPreferences(PREFS, Activity.MODE_PRIVATE)
    private val authClient = Identity.getAuthorizationClient(activity)
    @Volatile private var pendingSendBody: String? = null
    @Volatile private var pendingSetupOnly = false

    fun showSetupDialog() {
        val input = EditText(activity).apply {
            hint = "example@gmail.com"
            setSingleLine(true)
            setText(prefs.getString(KEY_RECIPIENT, "").orEmpty())
            setSelection(text.length)
        }
        AlertDialog.Builder(activity)
            .setTitle("Gmail自動送信の設定")
            .setMessage("5回の測定ごとに診断ログを自動送信します。送信に使うGoogleアカウントと同じGmailアドレスを入力してください。")
            .setView(input)
            .setPositiveButton("設定") { _, _ ->
                val address = input.text.toString().trim()
                if (!address.contains("@")) {
                    onStatus("Gmailアドレスが正しくありません")
                    return@setPositiveButton
                }
                prefs.edit().putString(KEY_RECIPIENT, address).apply()
                pendingSetupOnly = true
                authorizeAndContinue()
            }
            .setNegativeButton("キャンセル", null)
            .show()
    }

    fun recordMeasurement(summary: String) {
        val entries = loadEntries().toMutableList()
        entries += summary
        while (entries.size > 5) entries.removeAt(0)
        saveEntries(entries)

        if (entries.size < 5) {
            onStatus("Gmail自動記録 " + entries.size + "/5")
            return
        }

        val recipient = prefs.getString(KEY_RECIPIENT, "").orEmpty()
        if (recipient.isBlank()) {
            onStatus("5回分を保存しました。Gmail設定を1回行ってください")
            return
        }
        pendingSendBody = buildBatchBody(entries)
        authorizeAndContinue()
    }

    fun handleActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != REQUEST_CODE) return false
        if (data == null) {
            pendingSetupOnly = false
            onStatus("Gmail認証失敗 resultCode=" + resultCode + " / dataなし")
            return true
        }
        try {
            val result = authClient.getAuthorizationResultFromIntent(data)
            val token = result.accessToken
            if (token.isNullOrBlank()) {
                pendingSetupOnly = false
                onStatus("Gmail認証結果は返りましたがアクセストークンがありません / resultCode=" + resultCode)
            } else if (pendingSetupOnly) {
                pendingSetupOnly = false
                onStatus("Gmail自動送信を有効にしました")
                sendSavedIfReady(token)
            } else {
                sendPending(token)
            }
        } catch (e: ApiException) {
            pendingSetupOnly = false
            onStatus(
                "Gmail認証失敗 code=" + e.statusCode +
                    " / resultCode=" + resultCode +
                    " / " + (e.message ?: "詳細なし")
            )
        } catch (e: Throwable) {
            pendingSetupOnly = false
            onStatus(
                "Gmail認証エラー " + e.javaClass.simpleName +
                    " / resultCode=" + resultCode +
                    " / " + (e.message ?: "詳細なし")
            )
        }
        return true
    }

    private fun authorizeAndContinue() {
        val request = AuthorizationRequest.builder()
            .setRequestedScopes(listOf(Scope(GMAIL_SEND_SCOPE)))
            .build()

        authClient.authorize(request)
            .addOnSuccessListener { result ->
                if (result.hasResolution()) {
                    try {
                        activity.startIntentSenderForResult(
                            result.pendingIntent!!.intentSender,
                            REQUEST_CODE,
                            null, 0, 0, 0
                        )
                    } catch (e: Throwable) {
                        pendingSetupOnly = false
                        onStatus("Gmail認証画面を開けません: " + (e.message ?: "不明"))
                    }
                } else {
                    val token = result.accessToken
                    if (token.isNullOrBlank()) {
                        pendingSetupOnly = false
                        onStatus("Gmail認証トークンを取得できませんでした")
                    } else if (pendingSetupOnly) {
                        pendingSetupOnly = false
                        onStatus("Gmail自動送信を有効にしました")
                        sendSavedIfReady(token)
                    } else {
                        sendPending(token)
                    }
                }
            }
            .addOnFailureListener { e ->
                pendingSetupOnly = false
                if (e is ApiException) {
                    onStatus(
                        "Gmail認証開始失敗 code=" + e.statusCode +
                            " / " + (e.message ?: "詳細なし")
                    )
                } else {
                    onStatus(
                        "Gmail認証開始失敗 " + e.javaClass.simpleName +
                            " / " + (e.message ?: "詳細なし")
                    )
                }
            }
    }

    private fun sendSavedIfReady(token: String) {
        val saved = loadEntries()
        if (saved.size >= 5) {
            pendingSendBody = buildBatchBody(saved.takeLast(5))
            sendPending(token)
        }
    }

    private fun sendPending(accessToken: String) {
        val body = pendingSendBody ?: return
        val recipient = prefs.getString(KEY_RECIPIENT, "").orEmpty()
        if (recipient.isBlank()) {
            onStatus("Gmail送信先が未設定です")
            return
        }
        pendingSendBody = null

        Thread {
            try {
                val stamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.JAPAN).apply {
                    timeZone = TimeZone.getTimeZone("Asia/Tokyo")
                }.format(Date())
                val subjectText = "Green Reader 診断 5回分 " + stamp
                val subjectEncoded = "=?UTF-8?B?" +
                    Base64.encodeToString(subjectText.toByteArray(StandardCharsets.UTF_8), Base64.NO_WRAP) +
                    "?="

                val mime = buildString {
                    append("To: ").append(recipient).append("\r\n")
                    append("From: ").append(recipient).append("\r\n")
                    append("Subject: ").append(subjectEncoded).append("\r\n")
                    append("MIME-Version: 1.0\r\n")
                    append("Content-Type: text/plain; charset=UTF-8\r\n")
                    append("Content-Transfer-Encoding: 8bit\r\n\r\n")
                    append(body)
                }

                val raw = Base64.encodeToString(
                    mime.toByteArray(StandardCharsets.UTF_8),
                    Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
                )
                val conn = (URL("https://gmail.googleapis.com/gmail/v1/users/me/messages/send")
                    .openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 15000
                    readTimeout = 15000
                    doOutput = true
                    setRequestProperty("Authorization", "Bearer " + accessToken)
                    setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                }
                val json = "{\"raw\":\"" + raw + "\"}"
                conn.outputStream.use { it.write(json.toByteArray(StandardCharsets.UTF_8)) }
                val code = conn.responseCode
                if (code in 200..299) {
                    prefs.edit().remove(KEY_ENTRIES).apply()
                    activity.runOnUiThread { onStatus("5回分の診断ログをGmailへ自動送信しました") }
                } else {
                    activity.runOnUiThread { onStatus("Gmail送信失敗 HTTP " + code) }
                }
                conn.disconnect()
            } catch (e: Throwable) {
                activity.runOnUiThread { onStatus("Gmail送信エラー: " + (e.message ?: "不明")) }
            }
        }.start()
    }

    private fun buildBatchBody(entries: List<String>): String = buildString {
        appendLine("Green Reader Precision 自動診断ログ")
        appendLine("測定5回分")
        appendLine()
        entries.forEachIndexed { index, entry ->
            appendLine("===== 測定 " + (index + 1) + " =====")
            appendLine(entry)
            appendLine()
        }
    }

    private fun loadEntries(): List<String> {
        val raw = prefs.getString(KEY_ENTRIES, "").orEmpty()
        if (raw.isBlank()) return emptyList()
        return raw.split("\n---GREEN_READER_ENTRY---\n").filter { it.isNotBlank() }
    }

    private fun saveEntries(entries: List<String>) {
        prefs.edit().putString(KEY_ENTRIES, entries.joinToString("\n---GREEN_READER_ENTRY---\n")).apply()
    }
}
