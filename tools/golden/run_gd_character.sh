#!/usr/bin/env bash
# Headless test of the shared-skeleton character pipeline
# (godot/scripts/characters/*.gd and the RaceMini integration).
# Same scratch-copy pattern as run_gd_touch.sh: godot is never run inside the worktree.
# Usage: tools/golden/run_gd_character.sh        (final line: RESULT: OK|FAILED, exit 1 on failure)
# Env:   GD_SCRATCH, GODOT_BIN
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${GD_SCRATCH:-${TMPDIR:-/tmp}/storyforge-gd-run-character}"
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
OUT="$SCRATCH/character_test.log"
timeout 180 "$GODOT" --headless --path . -s res://tests/golden/character_test.gd -- \
	--backend=local "--save-dir=$SAVES" "$@" 2>&1 | grep -v PhantomCameraManager | tee "$OUT"
# RaceMini adds a PhantomCamera3D in _ready; the PhantomCameraManager autoload is registered by
# the editor plugin, so a headless run without the editor always logs these two errors for every
# RaceMini in the tree (same as run_gd_scene_smoke.sh). They are not failures of this test.
KNOWN="pcam_added|noise_3d_emitted"
if grep -q '^RESULT: OK$' "$OUT" && ! grep -E 'SCRIPT ERROR|Parse Error' "$OUT" | grep -qvE "$KNOWN"; then
	echo "RESULT: OK"
	exit 0
fi
echo "RESULT: FAILED"
exit 1
