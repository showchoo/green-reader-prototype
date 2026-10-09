package jp.example.greenreader.field

import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * Scoped Google Drive v3 REST calls using a short-lived Google Identity token.
 * Access is limited to files and folders created/opened by this app (drive.file).
 * Never persists access tokens or transmits them to anything but googleapis.com.
 */
internal class DriveBackupUploader(private val token: String) {
    class ApiException(val status: Int, message: String): Exception(message)

    private val api = "https://www.googleapis.com/drive/v3/files"
    private val uploadApi = "https://www.googleapis.com/upload/drive/v3/files"

    private fun open(url: String, method: String): HttpURLConnection {
        if (!url.startsWith("https://www.googleapis.com/"))
            error("Refusing unexpected Drive upload host")
        return (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 20000
            readTimeout = 180000
            setRequestProperty("Authorization", "Bearer " + token)
            setRequestProperty("Accept", "application/json")
            instanceFollowRedirects = false
        }
    }

    private fun consume(conn: HttpURLConnection): String {
        val code = conn.responseCode
        val body = try {
            (if (code in 200..299) conn.inputStream else conn.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
        } catch (_: Exception) { "" }
        if (code !in 200..299)
            throw ApiException(code, "Google Drive HTTP " + code + ": " + body.take(240))
        return body
    }

    private fun requestJson(method: String, url: String, body: JSONObject? = null): JSONObject {
        val conn = open(url, method)
        try {
            if (body != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            return JSONObject(consume(conn))
        } finally { conn.disconnect() }
    }

    private fun queryPart(q: String): String = URLEncoder.encode(q, "UTF-8")
    private fun driveEscape(s: String): String =
        s.replace("\\", "\\\\").replace("'", "\\'")

    private fun firstId(q: String): String? {
        val json = requestJson(
            "GET", api + "?q=" + queryPart(q) +
                "&fields=nextPageToken,files(id,name,mimeType)&pageSize=100"
        )
        return json.optJSONArray("files")?.optJSONObject(0)?.optString("id")
            ?.takeIf { it.isNotBlank() }
    }

    fun ensureFolder(): String {
        val name = DriveBackupScheduler.FOLDER_NAME
        val q = "name='" + driveEscape(name) +
            "' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        val existing = firstId(q)
        if (existing != null) return existing
        val meta = JSONObject().put("name", name)
            .put("mimeType", "application/vnd.google-apps.folder")
        val created = requestJson("POST", api + "?fields=id,name", meta)
        return created.getString("id")
    }

    private fun existingZipId(folderId: String, filename: String): String? {
        val q = "'" + driveEscape(folderId) + "' in parents and name='" +
            driveEscape(filename) + "' and trashed=false"
        return firstId(q)
    }

    /**
     * Create or REPLACE one same-named session ZIP; no per-scan duplicates.
     * Resumable endpoint supports ZIPs much larger than 5 MB on mobile links.
     */
    fun upsertSession(folderId: String, filename: String, zip: File): String {
        val id = existingZipId(folderId, filename)
        val path = if (id == null) uploadApi else uploadApi + "/" + id
        // HttpURLConnection may reject PATCH on some Android builds.
        // Google Drive supports POST with the method-override header.
        val method = "POST"
        val metadata = JSONObject().put("name", filename)
            .put("mimeType", "application/zip")
        if (id == null) metadata.put("parents", org.json.JSONArray().put(folderId))
        val setup = open(path + "?uploadType=resumable&fields=id,name", method)
        val sessionUrl: String
        try {
            if (id != null) setup.setRequestProperty("X-HTTP-Method-Override", "PATCH")
            setup.doOutput = true
            setup.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
            setup.setRequestProperty("X-Upload-Content-Type", "application/zip")
            setup.setRequestProperty("X-Upload-Content-Length", zip.length().toString())
            setup.outputStream.use { it.write(metadata.toString().toByteArray(Charsets.UTF_8)) }
            consume(setup)
            sessionUrl = setup.getHeaderField("Location")
                ?: error("Missing Drive resumable upload URL")
        } finally { setup.disconnect() }

        // PUT is a single final chunk through the resumable protocol. On
        // connection loss, the next WorkManager run looks up the same filename.
        val conn = open(sessionUrl, "PUT")
        try {
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/zip")
            conn.setFixedLengthStreamingMode(zip.length())
            zip.inputStream().buffered().use { input ->
                conn.outputStream.use { output -> input.copyTo(output, 64 * 1024) }
            }
            return JSONObject(consume(conn)).getString("id")
        } finally { conn.disconnect() }
    }
}
