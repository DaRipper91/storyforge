# Linux packaging (test builds)

`.github/workflows/package-linux.yml` builds `.deb`, `.rpm`, Arch `.pkg.tar.zst`
and an AppImage for **amd64** and **arm64**. It is test-only: it never creates
a tag or a GitHub release, never publishes to itch.io and uses no secrets. The
output is a 14-day workflow artifact per arch.

Run it from the Actions tab (workflow_dispatch, optional `version` input) or
by opening a PR that touches `nfpm.yaml`, `packaging/**`, the workflow,
`scripts/build.py` or `StoryForge.spec`.

## What is in a package

| Path | What |
|------|------|
| `/usr/bin/storyforge` | PyInstaller launcher: FastAPI server plus the Godot client (remote mode, needs `STORYFORGE_GEMINI_API_KEY`) |
| `/usr/lib/storyforge/storyforge-client` | Godot 4.6.2 Linux export (one binary, PCK embedded) |
| `/usr/bin/storyforge-offline` | wrapper: `exec storyforge-client "$@" -- --backend=local` (no server, no API key) |
| `/usr/bin/StoryForge_client` | symlink to the client; `launcher.py` looks for this name next to its own executable, without it the launcher stays in "headless mode" |
| `/usr/share/applications/storyforge.desktop`, `storyforge-offline.desktop` | menu entries |
| `/usr/share/icons/hicolor/scalable/apps/storyforge.svg`, `storyforge-offline.svg` | icons (`frontend/icon.svg`, `godot/icon.svg`) |

Arguments to `storyforge-offline` are Godot engine arguments (`--fullscreen`,
`--headless --version`). Game arguments go after a literal `--` and win over the
built-in `--backend=local` because the game takes the first `--backend=` it sees.

The AppImage holds `usr/bin/{storyforge,storyforge-client}`, `AppRun`, and the
offline `.desktop` + icon at the root. It starts the **offline client by
default**; `./StoryForge-*.AppImage web` runs the web launcher instead.

## Matrix

| arch | runner | Godot preset | glibc floor | AppImage ARCH |
|------|--------|--------------|-------------|---------------|
| amd64 | ubuntu-22.04 | Linux/X11 | 2.35 | x86_64 |
| arm64 | ubuntu-24.04-arm | Linux/ARM64 | 2.39 | aarch64 |

PyInstaller cannot cross-compile, so each leg builds natively. The arm64 leg is
`continue-on-error` so an ARM runner problem never hides the x86 result. The
Arch install test runs on amd64 only (no arm64 Arch image exists).

## Versions

`VERSION = <pyproject version or input>.dev<run_number>.g<sha7>`, e.g.
`0.2.0.dev57.g50ab6fd`, release `1`. Only digits, letters and dots, so it is
valid as a deb version, an rpm Version and a pacman `pkgver` (no `-`). It is
always marked, so a CI package cannot pass for a final one. Note it sorts
*newer* than the plain `0.2.0` in all three package managers. Pinned tools:
nfpm 2.48.0 (sha256 from its `checksums.txt`), appimagetool 1.9.1 and
type2-runtime 20251108 (sha256 recorded in the workflow), Godot 4.6.2 (SHA512-SUMS.txt).

## Getting and installing

```
gh run list --workflow package-linux.yml
gh run download <run-id> -n storyforge-linux-arm64    # or storyforge-linux-amd64
sha256sum -c SHA256SUMS.txt
```

```
sudo apt install ./storyforge_*.deb          # Debian/Ubuntu
sudo dnf install ./storyforge-*.rpm          # Fedora/RHEL family
sudo pacman -U storyforge-*.pkg.tar.zst      # Arch
chmod +x StoryForge-*.AppImage && ./StoryForge-*.AppImage
```

The `.rpm` for arm64 is the one to test on aarch64 Fedora.

## Dependencies (from evidence)

- The old `nfpm.yaml` declared GTK3 and WebKit2GTK. `StoryForge.spec` excludes
  `PyQt6`, `pywebview` and `webview`, and `launcher.py` only runs uvicorn and
  spawns the Godot client, so the bundle needs no GTK/WebKit. On current Fedora
  `webkit2gtk3` does not exist anyway (it is `webkit2gtk4.1`). Removed.
- The Godot editor binary (4.6.2 arm64) links only libc; X11, GL/Vulkan, audio,
  udev and fontconfig are `dlopen`ed. The export template was not inspected
  locally (1.2 GB download); the workflow prints `ldd` for both binaries.
- Hard dependency: glibc at or above the build floor. Recommends (deb/rpm) or
  depends (pacman, no weak deps in nfpm): GL, X11 client libs, libxkbcommon,
  fontconfig, udev. Fedora names were checked with `dnf repoquery`; Debian and
  Arch names are from knowledge and are exercised by the container install tests.
- No audio dependency is listed (ALSA/PulseAudio are dlopened); add one if the
  first display test shows silence.

## Known gaps

- Test builds only; nothing is published or signed.
- Nothing has been run with a display: only `--headless --version` is smoked.
- `nfpm.yaml` says `license: MIT` but the repo has no LICENSE file.
- The launcher needs the `StoryForge_client` symlink because it resolves the
  client relative to `sys.executable`; a proper fix is in `src/` (not done here).
- Debian/Ubuntu arm64 packages need glibc 2.39 (Ubuntu 24.04+).
