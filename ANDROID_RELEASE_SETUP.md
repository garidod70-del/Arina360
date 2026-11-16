# ARENA 360 Android release signing (one-time setup)

The in-app updater downloads the APK from the latest GitHub Release. Every update must be signed with the same private Android keystore. **Never commit the keystore or its passwords to this public repository.**

## 1. Create the permanent signing key

Run on a computer with Java/keytool installed (keep the resulting file and passwords in a safe backup):

```bash
keytool -genkeypair -v -keystore arena-upload-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias arena360
```

Choose and retain the keystore password and key password. Do not lose this file: without it, future updates cannot replace the installed app.

## 2. Add four GitHub Actions repository secrets

Convert the keystore file to one-line Base64:

- macOS/Linux: `base64 -w 0 arena-upload-key.jks`
- Windows PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("arena-upload-key.jks"))`

Open **Settings → Secrets and variables → Actions → New repository secret** in this repository and create:

- `ARENA_KEYSTORE_BASE64` — the complete Base64 output
- `ARENA_KEYSTORE_PASSWORD` — keystore password
- `ARENA_KEY_ALIAS` — `arena360`
- `ARENA_KEY_PASSWORD` — key password

Do not paste passwords or Base64 key data into issues, chat, source files, or commits. Keep a private backup of the keystore.

## 3. Publish the first installable baseline

After adding all four secrets, open **Actions → ARENA 360 Signed Release → Run workflow**. A successful run publishes the signed ARM64 APK as the latest GitHub Release.

The first install of this permanent-signing-key build must replace the older debug-signed app. Back up any important app data first; this prototype currently has no server-backed account/data migration. Uninstall the old app, then install the signed baseline APK. After that, later releases use the same key and can update over the existing app.

## 4. Later updates

Increase the `version:` build number in `apps/mobile/pubspec.yaml` for every release (for example, `0.1.0+3`, then `0.1.0+4`). Update `apps/mobile/version.json` with the matching `buildNumber`, version and release notes. Run the signed-release workflow again.

Android will show its normal package-installer confirmation. This is expected for sideloaded APK updates; the app cannot silently install updates on an ordinary, non-rooted phone.
