#!/usr/bin/env bash
# Replay tests/golden/routes against the GDScript LocalBackend, headless.
# Same scratch-copy pattern as run_gd_tests.sh: godot is never run inside the
# worktree (it rewrites project files); godot/ is copied to a scratch dir.
# Usage: tools/golden/run_gd_routes.sh [--flow=NAME] [--verbose]
# Env:   GD_ROUTES_DIR (default tests/golden/routes), GD_SCRATCH, GODOT_BIN
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRATCH="${GD_SCRATCH:-${TMPDIR:-/tmp}/storyforge-gd-run-routes}"
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
exec "$GODOT" --headless --path . -s res://tests/golden/run_routes.gd -- \
	"--routes=${GD_ROUTES_DIR:-$ROOT/tests/golden/routes}" "$@"
