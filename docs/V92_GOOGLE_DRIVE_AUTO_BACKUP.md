# Green Reader Precision v9.2 — Google Drive automatic scan backup

## Exact Drive destination

**My Drive / ゴルフ場スキャンデータ / Session_<session-id>.zip**

The app automatically creates its own `ゴルフ場スキャンデータ`
folder after account consent, using the limited Google Drive `drive.file`
scope. If the user has already created a different folder with the same
name outside this app, that folder might not be visible with the limited
scope, and a new same-named folder may be created. No broad read/write
permission to the user's entire Drive is requested.

One Drive ZIP per session. As scans finish, the session ZIP is replaced
in Drive rather than accumulating one ZIP per scan. Each ZIP preserves
`Putt_###/Scan_##_.../camera.jpg`, `metadata.json`, Depth CSV and
diagnostic text. Local `Download/GreenReaderRecords` is unchanged.

## How the user enables it

1. Open **保存データ** in Green Reader v9.2.
2. Press **Google Drive自動保存を開始**.
3. Select the desired Google account and grant the requested
   **only-app-created/opened Drive files** permission.
4. The switch changes to **ON**. Previous locally saved sessions from this
   app will also be included in its first sync.
5. Wait for the confirmation text; verify ZIPs exist in Drive's
   **ゴルフ場スキャンデータ** folder.
6. Press **Google Drive自動保存を停止** to stop uploads. Local saved scans are
   never deleted; already uploaded ZIPs remain in the user's Drive.

**No automatic uploads before explicit opt-in.**

## Android OAuth setup required before consent can work

Google authorization in an independently distributed Android APK needs an
OAuth 2.0 client registered under the Google Cloud project:
- Enable **Google Drive API**.
- Configure an OAuth consent screen with `drive.file`.
- In testing, add the intended account as a **test user**, if required.
- Create an **Android OAuth client** for package:
  `jp.showchoo.greenreader.precision`.
- Register the SHA-1 signing certificate fingerprint of the **same
  v6.9-compatible signing certificate** used by this app.
- Do not substitute the SHA-256 signing fingerprint for SHA-1.
- Configure release/publishing verification before broader distribution.

A connected **ChatGPT Google Drive plugin does not authorize the phone
application**: the phone must complete its own Android Google Identity
consent after the Cloud OAuth client is set up.

## Offline / reliability

- On each **completed local scan**, WorkManager schedules a network-constrained
  backup after a short debounce.
- The worker obtains a *fresh* short-lived Google Identity access token.
  Access tokens are never stored in files or preferences.
- A 6-hour periodic network-constrained sweep catches missed events;
  network errors use exponential backoff.
- Large ZIPs use Drive's resumable upload protocol, and re-runs look for
  the existing session filename rather than creating deliberate duplicates.
- Failed sync never deletes local scan data or marks its fingerprint synced.
- Google may request a renewed interactive consent. Worker cannot perform
  user interaction and displays a reauthorization status instead.
- No complete end-to-end Drive upload was performed in the CI environment;
  test on a real device and Google account before relying on cloud backup.

## Caveats and future hardening

- On Android 10+ (M07 supported), legacy app-owned MediaStore downloads are
  read for all complete `Session/Putt/Scan` records with
  `record_identity.json`. Earlier/other-app exported archives need manual
  migration.
- The ZIP is rebuilt per changed session. Upload at the end of a long golf
  session for a stable final archive and to avoid unnecessary transfers.
- Existing uploaded ZIPs are not automatically deleted when local records
  are deleted. Sync is one-way backup, not a destructive mirror.
- WorkManager run time is capped by Android; exceptionally large ZIP uploads
  may need chunk-resume state storage in a future version.
