#!/usr/bin/env bash
# Assemble a StoryForge AppDir and turn it into an AppImage.
#
# Usage: packaging/build-appimage.sh <x86_64|aarch64> <version> <outdir>
# Inputs (repo root, same as nfpm.yaml): dist/StoryForge, dist/storyforge-client
# Env:   APPIMAGETOOL  path to the (checksum-verified) appimagetool AppImage
#        APPIMAGE_RUNTIME  path to the (checksum-verified) type2 runtime file
set -euo pipefail

arch="${1:?arch (x86_64|aarch64)}"
version="${2:?version}"
outdir="${3:?output dir}"
: "${APPIMAGETOOL:?path to appimagetool}"
: "${APPIMAGE_RUNTIME:?path to type2 runtime}"

root="$(cd "$(dirname "$0")/.." && pwd)"
appdir="$(mktemp -d)/StoryForge.AppDir"
mkdir -p "$appdir/usr/bin" "$outdir"

install -m 0755 "$root/dist/StoryForge" "$appdir/usr/bin/storyforge"
install -m 0755 "$root/dist/storyforge-client" "$appdir/usr/bin/storyforge-client"
# launcher.py looks for StoryForge_client next to its own executable.
ln -s storyforge-client "$appdir/usr/bin/StoryForge_client"
install -m 0755 "$root/packaging/AppRun" "$appdir/AppRun"

# One .desktop + icon at the AppDir root; the AppImage defaults to offline mode.
sed 's|^Exec=.*|Exec=AppRun|' "$root/packaging/storyforge-offline.desktop" \
    > "$appdir/storyforge-offline.desktop"
install -m 0644 "$root/godot/icon.svg" "$appdir/storyforge-offline.svg"
ln -s storyforge-offline.svg "$appdir/.DirIcon"

out="$outdir/StoryForge-${version}-${arch}.AppImage"
ARCH="$arch" APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" --no-appstream \
    --runtime-file "$APPIMAGE_RUNTIME" "$appdir" "$out"
chmod +x "$out"
echo "built $out"
