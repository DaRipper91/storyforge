#!/usr/bin/env bash
# Regenerates the 35 race cards (godot/assets/characters/<id>.jpg, 800x1120, JPEG: the grain makes PNGs ~5 MB each) from the Codex concept sheets.
# Usage: tools/cards/gen_cards.sh <concept_dir> <out_dir> [slug ...]
# Cuts the FRONT-view figure out of each sheet (colour-keyed against the sheet background), puts it on a dark,
# group-tinted vignette and draws a group tag + name footer. Needs ImageMagick (magick). Concept sheets are NOT in the repo.
set -euo pipefail
SRC="${1:?concept dir}"; OUT="${2:?out dir}"; shift 2
mkdir -p "$OUT"
declare -A GROUP=( [voidwraith]=Cosmic [nullshade]=Cosmic [iron-locust]=Cosmic [embervein]=Cosmic [riftwalker]=Cosmic
  [solar-lord]=Primal [thornmimic]=Primal [cinderkin]=Primal [deep-tyrant]=Primal [grimcrow]=Primal
  [bloodweaver]=Eldritch [dreamhusk]=Eldritch [bonedrifter]=Eldritch [mindspider]=Eldritch [chaosling]=Eldritch
  [ironveil]=Mechanical [forgespawn]=Mechanical [cinderplate]=Mechanical [hexgear]=Mechanical [wirewraith]=Mechanical )
for s in ashenborn hollowsong veilborn thornweft ashcrown ironfast coreborn warpbred splitblood duskweft glitchkin fractureline emberpact fallenlight scaleworn; do GROUP[$s]=Humanoid; done
declare -A REGION_W=( [iron-locust]=360 [ashenborn]=470 )
declare -A FLOOD_FUZZ=( [ashcrown]=4 )          # pale subjects: a loose key would eat the figure
declare -A NO_POCKET_KEY=( [ashcrown]=1 )       # sheets whose side view starts closer to the front view
declare -A TINT=( [Cosmic]="#3a5fd0" [Primal]="#3f9a3a" [Eldritch]="#a23ab8" [Mechanical]="#d9822b" [Humanoid]="#c9a36a" )
FONT_ARGS=(); [ -n "${CARD_FONT:-}" ] && FONT_ARGS=(-font "$CARD_FONT")
slugs=("$@"); [ ${#slugs[@]} -eq 0 ] && slugs=("${!GROUP[@]}")
for slug in "${slugs[@]}"; do
  grp="${GROUP[$slug]}"; tint="${TINT[$grp]}"; id="${slug//-/}"; sheet="$SRC/$slug-v1.png"
  bg=$(magick "$sheet" -format '%[pixel:p{6,500}]' info:)
  region=$(mktemp --suffix=.png)
  RW="${REGION_W[$slug]:-405}"
  magick "$sheet" -crop ${RW}x850+0+95 +repage "$region"
  # contiguous flood-fill from the corners (keeps pale skin inside the figure), then a looser pass over the ground band
  keyed=$(mktemp --suffix=.png)
  magick "$region" -alpha set -fuzz ${FLOOD_FUZZ[$slug]:-9}% -fill none -draw "color 0,0 floodfill" -draw "color $((RW-1)),0 floodfill" \
    -fuzz 17% -draw "color 0,849 floodfill" -draw "color $((RW-1)),849 floodfill" "$keyed"
  # ground band: pockets of floor between the legs are not reachable from the corners, key them globally (feet area only)
  magick "$keyed" -region ${RW}x150+0+700 -fuzz 13% -transparent "$bg" +region "$keyed"
  # floor pockets between the legs and under robes are not reachable from the corners: key exact-background pixels (tight fuzz) in the lower 60%
  [ -z "${NO_POCKET_KEY[$slug]:-}" ] && magick "$keyed" -region ${RW}x510+0+340 -fuzz 5% -transparent "$bg" +region "$keyed"
  # keep only the biggest blob (drops slivers of the side-view figure), then crop around it
  box=$(magick "$keyed" -alpha extract -threshold 40% -define connected-components:keep-top=1 -connected-components 8 -trim -format '%@' info: 2>/dev/null || true)
  [ -z "$box" ] && box=$(magick "$keyed" -trim -format '%@' info:)
  W=${box%%x*}; rest=${box#*x}; H=${rest%%+*}; rest=${rest#*+}; X=${rest%%+*}; Y=${rest#*+}
  h=$(( H * 112 / 100 )); w=$(( h * 714 / 1000 )); cx=$(( X + W / 2 )); cy=$(( Y + H / 2 ))
  x0=$(( cx - w / 2 + 400 )); y0=$(( cy - h / 2 + 400 ))
  fig=$(mktemp --suffix=.png)
  magick "$keyed" -background none -bordercolor none -border 400 -crop "${w}x${h}+${x0}+${y0}" +repage -resize 800x1120! \
    -channel A -blur 0x0.7 +channel "$fig"
  rm -f "$keyed"
  magick -size 800x1120 radial-gradient:"$(magick -size 1x1 xc:"$tint" -modulate 38 -format '%[hex:u.p{0,0}]' info: | sed 's/^/#/')"-"#0a0807" \
    +noise Gaussian -attenuate 0.07 \( "$fig" -resize 88% \) -gravity south -geometry +0+110 -composite \
    -fill "#00000000" -stroke "$tint" -strokewidth 4 -draw "rectangle 10,10 789,1109" \
    -stroke none -fill "$tint" "${FONT_ARGS[@]}" -pointsize 34 -gravity northwest -annotate +32+24 "$(echo "$grp" | tr a-z A-Z)" \
    -fill "#f1e4c3" -pointsize 52 -gravity south -annotate +0+34 "$(echo "$slug" | tr a-z- A-Z' ')" \
    -quality 86 -sampling-factor 4:2:0 -strip "$OUT/$id.jpg"
  rm -f "$region" "$fig"
  echo "card $id ($grp)"
done
