#!/usr/bin/env bash
# Scene smoke (Step D2b): run Boot.tscn (project main scene) and a few scenes headless for a
# few frames in three builds and diff the distinct script-error lines:
#   local  = working tree, `--backend=local`
#   remote = working tree, default mode, no server running
#   base   = working tree with every tracked godot/ file changed vs HEAD restored from `git show HEAD:`
# Pass criterion: errors(local) is a subset of errors(remote) U errors(base). godot is never run in
# the worktree; every build is a scratch copy of godot/.
# Usage: tools/golden/run_gd_scene_smoke.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_DIR="${GD_SCRATCH:-/tmp/claude-1000/-home-daripper/6af3c5e8-f54c-42c7-bb38-55d615da2a13/scratchpad/gd-scene-smoke}"
GODOT="${GODOT_BIN:-/usr/bin/godot}"
PAT='SCRIPT ERROR|Parse Error|Compile Error|Invalid call|Invalid access|Nil'
SCENES=(res://scenes/UI_Overlay.tscn res://scenes/Creation.tscn res://scenes/Tabletop.tscn)

rm -rf "$BASE_DIR"; mkdir -p "$BASE_DIR"
copy_godot() {
	mkdir -p "$1"
	if command -v rsync >/dev/null 2>&1; then rsync -a --exclude='.godot' "$ROOT/godot/" "$1/"; else cp -a "$ROOT/godot/." "$1/"; rm -rf "$1/.godot"; fi
}
copy_godot "$BASE_DIR/new"
copy_godot "$BASE_DIR/old"
( cd "$ROOT" && git diff --name-only HEAD -- godot ) | while read -r f; do
	if git -C "$ROOT" cat-file -e "HEAD:$f" 2>/dev/null; then
		git -C "$ROOT" show "HEAD:$f" > "$BASE_DIR/old/${f#godot/}"
	fi
done
for d in new old; do ( cd "$BASE_DIR/$d" && "$GODOT" --headless --path . --import >/dev/null 2>&1 ); done

# run <label> <dir> <extra user args...>
run() {
	local label="$1" dir="$2"; shift 2
	local out="$BASE_DIR/$label.log"; : > "$out"
	( cd "$dir" && timeout 120 "$GODOT" --headless --path . --quit-after 120 -- "$@" --save-dir="$BASE_DIR/saves-$label" ) >> "$out" 2>&1
	for s in "${SCENES[@]}"; do
		( cd "$dir" && timeout 120 "$GODOT" --headless --path . -s res://tests/golden/scene_smoke.gd -- --scene="$s" --frames=90 "$@" --save-dir="$BASE_DIR/saves-$label" ) >> "$out" 2>&1
	done
	grep -E "$PAT" "$out" | grep -v PhantomCameraManager | sort -u > "$BASE_DIR/$label.errs"
	echo "$label: $(wc -l < "$BASE_DIR/$label.errs") distinct error lines"
}
# --save-dir is ignored by the pre-change build; the old build never touches saves.
run local  "$BASE_DIR/new" --backend=local
run remote "$BASE_DIR/new"
# pre-change build lacks scene_smoke.gd? it is a copy of the working tree, so it has it.
run base   "$BASE_DIR/old"
cat "$BASE_DIR/remote.errs" "$BASE_DIR/base.errs" | sort -u > "$BASE_DIR/allowed.errs"
echo "--- in local but not in remote/base:"
comm -23 "$BASE_DIR/local.errs" "$BASE_DIR/allowed.errs" | tee "$BASE_DIR/new-in-local.errs"
echo "--- in remote but not in base:"; comm -13 "$BASE_DIR/base.errs" "$BASE_DIR/remote.errs"
echo "--- in base but not in remote:"; comm -23 "$BASE_DIR/base.errs" "$BASE_DIR/remote.errs"
echo "--- in remote/base but not in local:"; comm -13 "$BASE_DIR/local.errs" "$BASE_DIR/allowed.errs"
if [ -s "$BASE_DIR/new-in-local.errs" ]; then echo "RESULT: FAILED"; exit 1; fi
echo "RESULT: OK"
