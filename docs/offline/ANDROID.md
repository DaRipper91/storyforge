# StoryForge offline on Android (debug APK)

Offline mode (`LocalBackend`, see `CLIENT_REWIRE.md`) runs the whole game in-process, so a phone needs no server.
On Android `PythonClient._resolve_mode()` falls back to `local` (explicit `--backend=`, env `STORYFORGE_BACKEND`
and `user://backend.cfg` still win). Everywhere else the default stays `remote`.

## How the CI works

Workflow: `.github/workflows/android-debug.yml` (ubuntu-24.04, x86-64; the aarch64 dev laptop cannot run the
Android build-tools). Triggers: push to `offline-port` touching `godot/**` or the workflow, plus manual
`workflow_dispatch`.

1. Download Godot 4.6.2-stable (linux x86_64) and its export templates from the official GitHub release and
   verify both against the release `SHA512-SUMS.txt`.
2. Install Android SDK pieces with `sdkmanager` (per the Godot 4.6 docs / `config.gradle` at 4.6.2-stable):
   platform-tools, build-tools 35.0.1, platforms;android-35, cmdline-tools;latest, cmake 3.10.2.4988404,
   NDK 28.1.13356709. JDK 17 (Temurin).
3. Write `~/.config/godot/editor_settings-4.6.tres` (SDK and JDK paths) and generate a throwaway debug keystore
   (alias `androiddebugkey`, password `android`), passed via `GODOT_ANDROID_KEYSTORE_DEBUG_*`. The keystore is
   never committed or uploaded, so every build is signed with a different key (see known gaps).
4. Run the GDScript suites (`run_gd_tests.sh`, `run_gd_routes.sh`, `run_gd_touch.sh`) on the pinned 4.6.2 binary (`GODOT_BIN`).
5. `--import`, then `--export-debug "Android"` (preset in `godot/export_presets.cfg`: no Gradle, arm64-v8a only,
   `com.daripper91.storyforge`, version `0.1.0-offline`, INTERNET permission kept).
6. Fail if the APK is missing or under 5 MB; print the APK contents and `apksigner verify`; upload artifact
   `storyforge-debug-apk` (14 days). Nothing is released or published.

## Get the APK

```
gh run list --workflow android-debug.yml --branch offline-port --limit 3
gh run download <run-id> -n storyforge-debug-apk -D build/android
```
Or open the run on the GitHub Actions page and download the `storyforge-debug-apk` artifact (zip).

## Install on a Pixel / Galaxy

1. Phone: Settings > About > tap Build number 7 times, then Developer options > enable USB debugging.
2. Plug in via USB, accept the "Allow USB debugging" prompt.
3. `adb devices` (must list the phone as `device`, not `unauthorized`).
4. `adb install -r build/android/storyforge-debug.apk`
   - `INSTALL_FAILED_UPDATE_INCOMPATIBLE`: the signing key differs from the installed build (CI makes a new
     key each run). `adb uninstall com.daripper91.storyforge` first (this wipes the offline save).

## Logs

```
adb logcat -s godot
adb logcat -c && adb logcat | grep -iE "godot|storyforge|AndroidRuntime"   # crashes
```
Saves live in the app's `user://` dir, not shared storage.

## Known gaps

- **Touch controls are new and unverified on a device.** `TouchControls` (see `TOUCH_CONTROLS.md`) draws a floating
  joystick, a camera-drag area with pinch zoom and six buttons when running on Android/iOS (or with `--touch`).
  Headless tests cover the logic; feel, sizing and the mouse-from-touch suppression have not been tried on a phone.
  Still missing: lock-on (`lock_on`/Q) has no button, number-key character select (1-4), the `I` stat-panel toggle,
  Esc/back handling (freeform is cancelled by submitting an empty line), controller hints are replaced by a blank hint
  line, and creation/lobby screens are the original mouse layouts (some buttons are below 9 mm, see TOUCH_CONTROLS.md).
  A Bluetooth gamepad still works and is still the better way to play.
- **Renderer.** Project is tagged "Forward Plus", but `rendering/renderer/rendering_method.mobile` is not set in
  `project.godot`; Godot's default for the mobile override is `mobile`, so Android should run the Mobile
  renderer, not Forward+. Unverified on device; not changed in this step. Plugins (toon shader, multimesh scatter)
  have not been checked against the Mobile renderer.
- **Orientation/window.** `display/window/handheld/orientation` is unset (default landscape); viewport 1280x720.
- **Debug key rotates per CI run**, so updates need an uninstall (see above).
- **Never run on a device yet.** The CI itself has not run at the time of writing.
- **PhantomCamera** singleton errors at import are known and benign on desktop; not yet observed on Android.
