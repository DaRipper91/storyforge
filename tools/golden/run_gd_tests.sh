#!/usr/bin/env bash
# Replay tests/golden/fixtures against the GDScript port, headless.
# ONLY engine entry point: godot is never run inside the worktree (it rewrites
# project files); godot/ is copied to a fresh scratch dir every time.
# Usage: tools/golden/run_gd_tests.sh [--module=grid] [--verbose]
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${GD_SCRATCH:-/tmp/claude-1000/-home-daripper/6af3c5e8-f54c-42c7-bb38-55d615da2a13/scratchpad/gd-run}"
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
exec "$GODOT" --headless --path . -s res://tests/golden/run_golden.gd -- \
	"--fixtures=${GD_FIXTURES:-$ROOT/tests/golden/fixtures}" "$@"
