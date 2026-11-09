#!/usr/bin/env bash
# Headless smoke test of the client's local-backend path (real PythonClient autoload,
# `--backend=local`, throwaway save dir). Same scratch-copy pattern as run_gd_tests.sh:
# godot is never run inside the worktree; godot/ is copied to a scratch dir first.
# Usage: tools/golden/run_gd_smoke.sh
# Env:   GD_SCRATCH, GODOT_BIN
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${GD_SCRATCH:-${TMPDIR:-/tmp}/storyforge-gd-run-smoke}"
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
exec "$GODOT" --headless --path . -s res://tests/golden/smoke_local.gd -- \
	--backend=local "--save-dir=$SAVES" "$@"
