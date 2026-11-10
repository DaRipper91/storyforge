#!/usr/bin/env bash
# Headless layout test of the character-creation screen (godot/tests/golden/ui_layout_test.gd):
# touch-target sizes, overlaps, safe area, stable footer, carousel swipe at several viewport sizes.
# Same scratch-copy pattern as run_gd_smoke.sh: godot is never run inside the worktree.
# Usage: tools/golden/run_gd_ui.sh        (final line: RESULT: OK|FAILED, exit 1 on failure)
# Env:   GD_SCRATCH, GODOT_BIN
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${GD_SCRATCH:-${TMPDIR:-/tmp}/storyforge-gd-run-ui}"
GODOT="${GODOT_BIN:-/usr/bin/godot}"

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
if command -v rsync >/dev/null 2>&1; then
	rsync -a --exclude='.godot' "$ROOT/godot/" "$SCRATCH/"
else
	cp -a "$ROOT/godot/." "$SCRATCH/"
	rm -rf "$SCRATCH/.godot"
fi
SAVES="$(mktemp -d "$SCRATCH/saves.XXXXXX")"

cd "$SCRATCH" || exit 2
"$GODOT" --headless --path . --import >/dev/null 2>&1
OUT="$SCRATCH/ui_layout_test.log"
timeout 180 "$GODOT" --headless --path . -s res://tests/golden/ui_layout_test.gd -- \
	--backend=local "--save-dir=$SAVES" "$@" 2>&1 | grep -v PhantomCameraManager | tee "$OUT"
# RaceMini adds a PhantomCamera3D in _ready; the PhantomCameraManager autoload is registered by
# the editor plugin, so a headless run always logs these two errors per RaceMini (KNOWN noise).
KNOWN="pcam_added|noise_3d_emitted"
if grep -q '^RESULT: OK$' "$OUT" && ! grep -E 'SCRIPT ERROR|Parse Error' "$OUT" | grep -qvE "$KNOWN"; then
	echo "RESULT: OK"
	exit 0
fi
echo "RESULT: FAILED"
exit 1
