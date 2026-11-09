#!/usr/bin/env bash
# Regenerates every README asset under docs/assets/. Needs: uv (or python3), rsvg-convert, magick.
# SVG outputs are byte-identical across runs. PNG sheets/social preview are written with metadata
# stripped; compare with `./build.sh --hash` (SVG sha256 + PNG pixel hashes).
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS="$(dirname "$HERE")"
REPO="$(cd "$ASSETS/../.." && pwd)"
cd "$HERE"

PY=(python3)
command -v uv >/dev/null && PY=(uv run --project "$REPO" python)

python3 gen_atlas.py
python3 gen_diagrams.py
"${PY[@]}" gen_sheets.py
rsvg-convert -w 1280 -h 640 "$ASSETS/social-preview.svg" -o "$ASSETS/social-preview.png"
magick "$ASSETS/social-preview.png" -strip -define png:exclude-chunk=date,time,tIME,iTXt,tEXt,zTXt "$ASSETS/social-preview.png"

if [[ "${1:-}" == "--hash" ]]; then
  ( cd "$ASSETS"
    sha256sum ./*.svg
    for p in ./*.png; do printf '%s  ' "$(magick "$p" -format '%#' info:)"; echo "$p"; done
    sha256sum ./*.png )
fi
