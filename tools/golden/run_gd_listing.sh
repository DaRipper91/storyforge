#!/usr/bin/env bash
# Headless regression test for the export-only item-loading bug (godot/scripts/util/resource_listing.gd).
# Same scratch-copy pattern as run_gd_touch.sh: godot is never run inside the worktree.
# Usage: tools/golden/run_gd_listing.sh        (final line: RESULT: OK|FAILED, exit 1 on failure)
# Env:   GD_SCRATCH, GODOT_BIN
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${GD_SCRATCH:-${TMPDIR:-/tmp}/storyforge-gd-listing}"
GODOT="${GODOT_BIN:-/usr/bin/godot}"

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
if command -v rsync >/dev/null 2>&1; then
	rsync -a --exclude='.godot' "$ROOT/godot/" "$SCRATCH/"
else
	cp -a "$ROOT/godot/." "$SCRATCH/"
	rm -rf "$SCRATCH/.godot"
fi

cd "$SCRATCH" || exit 2
"$GODOT" --headless --path . --import >/dev/null 2>&1
OUT="$SCRATCH/resource_listing_test.log"
timeout 120 "$GODOT" --headless --path . -s res://tests/golden/resource_listing_test.gd -- \
	--backend=local "--save-dir=$SCRATCH/saves" "$@" 2>&1 | grep -v PhantomCameraManager | tee "$OUT"
if grep -q '^RESULT: OK$' "$OUT" && ! grep -qE 'SCRIPT ERROR|Parse Error' "$OUT"; then
	echo "RESULT: OK"
	exit 0
fi
echo "RESULT: FAILED"
exit 1
