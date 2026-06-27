/**
 * 8-bit walking sprites — one unique set per race.
 *
 * Each frame is a flat 8×8 = 64-element palette-index array.
 * Palette (per renderSprite call):
 *   0 = transparent
 *   1 = accent color  (race-specific — glows, feathers, bone, etc.)
 *   2 = charColor     (the character's theme color)
 *   3 = dark shade    (auto-darkened charColor — shadows, shoes, outlines)
 *
 * Frame sequence per race: [leftStep, midStride, rightStep, midStride]
 * flipH() is called automatically when the character moves left.
 */

// ─────────────────────────── palette ────────────────────────────────────────

/**
 * Per-race override for palette slot 1 (the "accent" / skin / glow color).
 * Anything not listed here gets the default parchment #f4ead4.
 */
export const RACE_ACCENT_COLORS = {
  voidwraith:  '#9ac8ff',  // spectral blue core glow
  nullshade:   '#8899aa',  // shadowy grey glint
  ironlocust:  '#d4b820',  // compound-eye gold
  embervein:   '#ff6600',  // lava crack orange
  solarlord:   '#ffffc0',  // sun-bright feathers
  deeptyrant:  '#00d4cc',  // bioluminescent teal
  dreamhusk:   '#d8b4ff',  // spore-mist lavender
  bonedrifter: '#ddddd0',  // bleached bone white
  mindspider:  '#aaffdd',  // translucent emerald shimmer
  ashenborn:   '#ff6644',  // charred ember survivor
  hollowsong:  '#cc88ff',  // inverted magic residue
  veilborn:    '#6677aa',  // deep shadow adaptation
  thornweft:   '#66aa44',  // bark-skin growth
  ashcrown:    '#eeeebb',  // fading translucent regal
  ironfast:    '#999999',  // calcified bone grey
  coreborn:    '#ff4422',  // deep-core pull
  warpbred:    '#aa2200',  // paradox-asked blood
  splitblood:  '#884422',  // two-half conflict
  duskweft:    '#aaaaff',  // sideways flicker
  glitchkin:   '#00ffaa',  // self-modified circuitry
  fractureline:'#ffaa00',  // split-memory gold
  emberpact:   '#ff4444',  // freed infernal fire
  fallenlight: '#ffff99',  // severed divine glow
  scaleworn:   '#336633',  // collapsed draconic green
  ironveil:    '#c8e8ff',  // razor-thin steel shimmer
  forgespawn:  '#ff8800',  // liquid-metal forge glow
  cinderplate: '#ff4400',  // molten core bleed
  hexgear:     '#88ffcc',  // modular circuit trace
  wirewraith:  '#ffff44',  // exposed-nerve charge
};

// ─────────────────────────── sprite data ────────────────────────────────────

/* prettier-ignore */
export const RACE_WALK_FRAMES = {

  // ══ VOIDWRAITH ══ spectral orb + trailing wisps, no solid legs ═══════════
  voidwraith: [
    // F0 — wisps spread wide
    [0,0,2,2,2,2,0,0,
     0,2,1,2,2,1,2,0,
     0,2,2,1,2,2,2,0,
     0,0,2,2,2,2,0,0,
     2,0,0,2,2,0,0,2,
     2,0,0,2,2,0,0,2,
     0,2,0,0,0,0,2,0,
     0,0,2,0,0,2,0,0],
    // F1 — wisps together
    [0,0,2,2,2,2,0,0,
     0,2,1,2,2,1,2,0,
     0,2,2,1,2,2,2,0,
     0,0,2,2,2,2,0,0,
     0,2,0,2,2,0,2,0,
     0,2,0,2,2,0,2,0,
     0,0,2,0,0,2,0,0,
     0,0,0,2,2,0,0,0],
    // F2 — wisps diagonal
    [0,0,2,2,2,2,0,0,
     0,2,1,2,2,1,2,0,
     0,2,2,1,2,2,2,0,
     0,0,2,2,2,2,0,0,
     2,0,0,2,2,0,0,2,
     0,2,0,2,2,0,2,0,
     0,0,2,0,0,2,0,0,
     0,2,0,0,0,0,0,2],
    // F3 = F1
    [0,0,2,2,2,2,0,0,
     0,2,1,2,2,1,2,0,
     0,2,2,1,2,2,2,0,
     0,0,2,2,2,2,0,0,
     0,2,0,2,2,0,2,0,
     0,2,0,2,2,0,2,0,
     0,0,2,0,0,2,0,0,
     0,0,0,2,2,0,0,0],
  ],

  // ══ NULLSHADE ══ amorphous shadow blob, single shifting eye ═══════════════
  nullshade: [
    // F0 — blob shifted left
    [0,2,2,2,2,0,0,0,
     2,2,2,2,2,2,0,0,
     2,2,1,2,2,2,2,0,
     2,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,0,2,2,2,0,0,0,
     0,2,0,2,0,0,0,0,
     0,0,0,0,0,0,0,0],
    // F1 — blob centred
    [0,0,2,2,2,2,0,0,
     0,2,2,2,2,2,2,0,
     0,2,2,1,2,2,2,0,
     0,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,0,2,2,2,0,0,0,
     0,0,0,2,0,0,0,0,
     0,0,0,0,0,0,0,0],
    // F2 — blob shifted right
    [0,0,0,2,2,2,2,0,
     0,0,2,2,2,2,2,2,
     0,0,2,2,2,1,2,2,
     0,0,2,2,2,2,2,2,
     0,0,0,2,2,2,2,0,
     0,0,0,0,2,2,0,0,
     0,0,0,0,0,2,0,2,
     0,0,0,0,0,0,0,0],
    // F3 = F1
    [0,0,2,2,2,2,0,0,
     0,2,2,2,2,2,2,0,
     0,2,2,1,2,2,2,0,
     0,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,0,2,2,2,0,0,0,
     0,0,0,2,0,0,0,0,
     0,0,0,0,0,0,0,0],
  ],

  // ══ IRONLOCUST ══ chitinous insect, antennae, 6 legs ═════════════════════
  ironlocust: [
    // F0 — front legs up, rear legs forward
    [3,0,3,3,3,3,0,0,
     0,3,0,1,1,0,3,0,
     0,3,3,3,3,3,3,0,
     0,2,2,2,2,2,2,0,
     3,0,2,2,2,2,0,3,
     3,0,0,2,2,0,0,3,
     0,3,0,0,0,0,3,0,
     0,0,3,0,0,3,0,0],
    // F1 — legs tucked
    [3,0,3,3,3,3,0,0,
     0,3,0,1,1,0,3,0,
     0,3,3,3,3,3,3,0,
     0,2,2,2,2,2,2,0,
     0,3,2,2,2,2,3,0,
     3,0,0,2,2,0,0,3,
     0,3,0,2,2,0,3,0,
     0,0,3,0,0,3,0,0],
    // F2 — front legs down, middle up
    [3,0,3,3,3,3,0,0,
     0,3,0,1,1,0,3,0,
     0,3,3,3,3,3,3,0,
     0,2,2,2,2,2,2,0,
     0,3,0,2,2,0,3,0,
     3,0,2,2,2,2,0,3,
     3,0,0,2,2,0,0,3,
     0,3,0,0,0,0,3,0],
    // F3 = F1
    [3,0,3,3,3,3,0,0,
     0,3,0,1,1,0,3,0,
     0,3,3,3,3,3,3,0,
     0,2,2,2,2,2,2,0,
     0,3,2,2,2,2,3,0,
     3,0,0,2,2,0,0,3,
     0,3,0,2,2,0,3,0,
     0,0,3,0,0,3,0,0],
  ],

  // ══ EMBERVEIN ══ massive molten leviathan, lava cracks, VERY WIDE ════════
  embervein: [
    // F0 — stomp left (body barely moves, just feet)
    [2,2,2,2,2,2,2,2,
     2,2,1,2,2,1,2,2,
     2,2,2,2,2,2,2,2,
     2,2,1,2,2,2,1,2,
     2,2,2,2,2,2,2,2,
     0,2,2,1,1,2,2,0,
     3,2,2,0,0,2,2,3,
     3,3,0,0,0,0,3,0],
    // F1 — feet together
    [2,2,2,2,2,2,2,2,
     2,2,1,2,2,1,2,2,
     2,2,2,2,2,2,2,2,
     2,2,1,2,2,2,1,2,
     2,2,2,2,2,2,2,2,
     0,2,2,1,1,2,2,0,
     0,3,2,2,2,2,3,0,
     0,3,3,0,0,3,3,0],
    // F2 — stomp right
    [2,2,2,2,2,2,2,2,
     2,2,1,2,2,1,2,2,
     2,2,2,2,2,2,2,2,
     2,2,1,2,2,2,1,2,
     2,2,2,2,2,2,2,2,
     0,2,2,1,1,2,2,0,
     3,2,2,0,0,2,2,3,
     0,3,3,0,0,0,3,3],
    // F3 = F1
    [2,2,2,2,2,2,2,2,
     2,2,1,2,2,1,2,2,
     2,2,2,2,2,2,2,2,
     2,2,1,2,2,2,1,2,
     2,2,2,2,2,2,2,2,
     0,2,2,1,1,2,2,0,
     0,3,2,2,2,2,3,0,
     0,3,3,0,0,3,3,0],
  ],

  // ══ RIFTWALKER ══ lean phase-hunter with tail ════════════════════════════
  riftwalker: [
    // F0 — left foot, tail angled
    [0,0,2,2,2,2,0,0,
     0,0,2,1,1,2,0,0,
     0,0,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,2,0,2,2,0,0,2,
     0,0,0,2,2,0,0,2,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — neutral, tail low
    [0,0,2,2,2,2,0,0,
     0,0,2,1,1,2,0,0,
     0,0,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,0,2,2,2,0,0,2,
     0,0,2,2,2,0,0,2,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — right foot, tail angled other way
    [0,0,2,2,2,2,0,0,
     0,0,2,1,1,2,0,0,
     0,0,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,2,0,2,2,0,0,2,
     0,0,0,2,2,0,0,2,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,0,2,2,2,2,0,0,
     0,0,2,1,1,2,0,0,
     0,0,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,0,2,2,2,0,0,2,
     0,0,2,2,2,0,0,2,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ SOLARLORD ══ celestial avian, wings span full 8 wide ═════════════════
  solarlord: [
    // F0 — wings mid-stroke, left leg
    [0,0,0,1,1,0,0,0,
     0,0,1,1,1,2,0,0,
     2,0,2,1,1,2,0,2,
     2,2,2,2,2,2,2,2,
     0,2,2,2,2,2,2,0,
     0,0,2,2,2,0,0,0,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — wings raised
    [0,0,0,1,1,0,0,0,
     0,0,1,1,1,2,0,0,
     2,2,0,1,1,0,2,2,
     2,2,0,0,0,0,2,2,
     0,2,2,2,2,2,2,0,
     0,0,2,2,2,0,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — wings mid-stroke, right leg
    [0,0,0,1,1,0,0,0,
     0,0,1,1,1,2,0,0,
     2,0,2,1,1,2,0,2,
     2,2,2,2,2,2,2,2,
     0,2,2,2,2,2,2,0,
     0,0,2,2,2,0,0,0,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,0,0,1,1,0,0,0,
     0,0,1,1,1,2,0,0,
     2,2,0,1,1,0,2,2,
     2,2,0,0,0,0,2,2,
     0,2,2,2,2,2,2,0,
     0,0,2,2,2,0,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ THORNMIMIC ══ bark-skinned shapeshifter, thorns at shoulders + head ══
  thornmimic: [
    // F0 — left foot, left thorn raised
    [0,3,0,3,3,0,3,0,
     0,3,3,3,3,3,3,0,
     0,3,2,1,1,2,3,0,
     3,2,2,2,2,2,2,3,
     3,2,3,2,2,3,2,3,
     0,3,2,2,2,2,3,0,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — mid, thorns even
    [0,3,0,3,3,0,3,0,
     0,3,3,3,3,3,3,0,
     0,3,2,1,1,2,3,0,
     3,2,2,2,2,2,2,3,
     0,3,2,2,2,2,3,0,
     0,3,2,2,2,2,3,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — right foot, right thorn raised
    [0,3,0,3,3,0,3,0,
     0,3,3,3,3,3,3,0,
     0,3,2,1,1,2,3,0,
     3,2,2,2,2,2,2,3,
     3,2,3,2,2,3,2,3,
     0,3,2,2,2,2,3,0,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,3,0,3,3,0,3,0,
     0,3,3,3,3,3,3,0,
     0,3,2,1,1,2,3,0,
     3,2,2,2,2,2,2,3,
     0,3,2,2,2,2,3,0,
     0,3,2,2,2,2,3,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ CINDERKIN ══ tiny fire-sprite, crystal cluster crown, compact form ════
  cinderkin: [
    // F0 — left foot
    [0,0,1,1,1,0,0,0,
     0,1,1,2,1,1,0,0,
     0,0,1,1,1,0,0,0,
     0,0,2,2,2,0,0,0,
     0,2,0,2,2,0,2,0,
     0,0,0,2,2,0,0,0,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — neutral
    [0,0,1,1,1,0,0,0,
     0,1,1,2,1,1,0,0,
     0,0,1,1,1,0,0,0,
     0,0,2,2,2,0,0,0,
     0,0,2,2,2,0,0,0,
     0,0,2,2,2,0,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — right foot
    [0,0,1,1,1,0,0,0,
     0,1,1,2,1,1,0,0,
     0,0,1,1,1,0,0,0,
     0,0,2,2,2,0,0,0,
     0,2,0,2,2,0,2,0,
     0,0,0,2,2,0,0,0,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,0,1,1,1,0,0,0,
     0,1,1,2,1,1,0,0,
     0,0,1,1,1,0,0,0,
     0,0,2,2,2,0,0,0,
     0,0,2,2,2,0,0,0,
     0,0,2,2,2,0,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ DEEPTYRANT ══ large cephalopodic mantle, tentacles writhe below ═══════
  deeptyrant: [
    // F0 — tentacles spread (set A)
    [0,2,2,2,2,2,0,0,
     2,2,1,2,2,1,2,0,
     2,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     3,0,3,3,3,3,0,3,
     3,0,3,0,3,0,0,3,
     0,3,0,3,0,3,0,0,
     0,0,3,0,0,0,3,0],
    // F1 — tentacles tucked
    [0,2,2,2,2,2,0,0,
     2,2,1,2,2,1,2,0,
     2,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,3,3,3,3,3,3,0,
     3,0,3,0,3,0,3,0,
     3,0,0,3,0,3,0,0,
     0,3,0,0,3,0,0,0],
    // F2 — tentacles spread (set B, alternated)
    [0,2,2,2,2,2,0,0,
     2,2,1,2,2,1,2,0,
     2,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     3,0,3,3,3,3,0,3,
     0,3,0,3,0,3,0,0,
     3,0,3,0,3,0,3,0,
     0,0,0,3,0,0,3,0],
    // F3 = F1
    [0,2,2,2,2,2,0,0,
     2,2,1,2,2,1,2,0,
     2,2,2,2,2,2,2,0,
     0,2,2,2,2,2,0,0,
     0,3,3,3,3,3,3,0,
     3,0,3,0,3,0,3,0,
     3,0,0,3,0,3,0,0,
     0,3,0,0,3,0,0,0],
  ],

  // ══ GRIMCROW ══ obsidian-feathered, wings wrap like a dark cloak ══════════
  grimcrow: [
    // F0 — hop (body slightly lowered, left foot)
    [0,0,3,3,3,3,0,0,
     0,0,3,1,0,3,0,0,
     0,3,3,3,3,3,0,0,
     2,2,3,3,3,3,2,2,
     2,2,3,3,3,3,2,2,
     2,2,2,3,3,2,2,0,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — hop (body raised, wings slightly open)
    [0,0,3,3,3,3,0,0,
     0,0,3,1,0,3,0,0,
     0,3,3,3,3,3,3,0,
     2,2,3,3,3,3,2,0,
     0,2,3,3,3,3,2,0,
     0,2,2,3,3,2,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — hop down (right foot)
    [0,0,3,3,3,3,0,0,
     0,0,3,1,0,3,0,0,
     0,3,3,3,3,3,0,0,
     2,2,3,3,3,3,2,2,
     2,2,3,3,3,3,2,2,
     2,2,2,3,3,2,2,0,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,0,3,3,3,3,0,0,
     0,0,3,1,0,3,0,0,
     0,3,3,3,3,3,3,0,
     2,2,3,3,3,3,2,0,
     0,2,3,3,3,3,2,0,
     0,2,2,3,3,2,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ BLOODWEAVER ══ tall regal horror, dramatic flowing cape ═══════════════
  bloodweaver: [
    // F0 — cape billows left, left leg
    [0,0,2,2,2,0,0,0,
     0,0,2,1,2,2,0,0,
     0,0,2,2,2,2,0,0,
     2,0,2,2,2,2,0,0,
     2,0,0,2,2,0,0,2,
     2,0,0,2,2,0,0,2,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — cape even
    [0,0,2,2,2,0,0,0,
     0,0,2,1,2,2,0,0,
     0,0,2,2,2,2,0,0,
     2,0,2,2,2,2,0,2,
     0,2,0,2,2,0,2,0,
     0,2,0,2,2,0,2,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — cape billows right, right leg
    [0,0,2,2,2,0,0,0,
     0,0,2,1,2,2,0,0,
     0,0,2,2,2,2,0,0,
     0,0,2,2,2,2,0,2,
     2,0,0,2,2,0,0,2,
     2,0,0,2,2,0,0,2,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,0,2,2,2,0,0,0,
     0,0,2,1,2,2,0,0,
     0,0,2,2,2,2,0,0,
     2,0,2,2,2,2,0,2,
     0,2,0,2,2,0,2,0,
     0,2,0,2,2,0,2,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ DREAMHUSK ══ spore-borne entity, haze of particles around body ════════
  dreamhusk: [
    // F0 — spores scattered, left foot
    [1,0,2,2,2,2,0,1,
     0,0,2,1,1,2,0,0,
     1,0,2,2,2,2,0,0,
     0,0,2,2,2,2,0,1,
     1,2,0,2,2,0,2,0,
     0,0,0,2,2,0,0,1,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — spores drifted
    [0,1,2,2,2,2,1,0,
     0,0,2,1,1,2,0,0,
     0,0,2,2,2,2,0,1,
     1,0,2,2,2,2,0,0,
     0,2,0,2,2,0,2,0,
     1,0,0,2,2,0,0,1,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — spores shifted, right foot
    [1,0,2,2,2,2,0,1,
     0,0,2,1,1,2,0,0,
     0,1,2,2,2,2,0,0,
     0,0,2,2,2,2,1,0,
     1,2,0,2,2,0,2,0,
     0,0,0,2,2,0,0,1,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,1,2,2,2,2,1,0,
     0,0,2,1,1,2,0,0,
     0,0,2,2,2,2,0,1,
     1,0,2,2,2,2,0,0,
     0,2,0,2,2,0,2,0,
     1,0,0,2,2,0,0,1,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ BONEDRIFTER ══ parasitic skeleton-rewriter, bone spurs + skull face ═══
  bonedrifter: [
    // F0 — bone spurs out, left foot
    [0,3,3,3,3,3,0,0,
     0,3,1,3,3,1,3,0,
     0,0,3,3,3,3,0,0,
     3,0,2,2,2,2,0,3,
     3,0,3,2,2,3,0,3,
     0,0,2,2,2,2,0,0,
     0,0,3,0,0,3,0,0,
     0,3,3,0,0,0,0,0],
    // F1 — spurs tucked
    [0,3,3,3,3,3,0,0,
     0,3,1,3,3,1,3,0,
     0,0,3,3,3,3,0,0,
     3,0,2,2,2,2,0,3,
     0,3,2,2,2,2,3,0,
     0,3,2,2,2,2,3,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — bone spurs out, right foot
    [0,3,3,3,3,3,0,0,
     0,3,1,3,3,1,3,0,
     0,0,3,3,3,3,0,0,
     3,0,2,2,2,2,0,3,
     3,0,3,2,2,3,0,3,
     0,0,2,2,2,2,0,0,
     0,0,3,0,0,3,0,0,
     0,0,0,0,0,3,3,0],
    // F3 = F1
    [0,3,3,3,3,3,0,0,
     0,3,1,3,3,1,3,0,
     0,0,3,3,3,3,0,0,
     3,0,2,2,2,2,0,3,
     0,3,2,2,2,2,3,0,
     0,3,2,2,2,2,3,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],

  // ══ MINDSPIDER ══ translucent arachnid, cephalothorax + abdomen + 8 legs ═
  mindspider: [
    // F0 — front+rear legs up, middle down
    [0,0,0,2,2,0,0,0,
     3,0,2,2,2,2,0,3,
     0,3,2,2,2,2,3,0,
     3,0,0,2,2,0,0,3,
     0,3,0,2,2,0,3,0,
     0,0,0,2,2,0,0,0,
     0,0,0,2,2,0,0,0,
     0,0,0,1,1,0,0,0],
    // F1 — front+rear down, middle up
    [0,0,0,2,2,0,0,0,
     0,3,2,2,2,2,3,0,
     3,0,2,2,2,2,0,3,
     0,3,0,2,2,0,3,0,
     3,0,0,2,2,0,0,3,
     0,0,0,2,2,0,0,0,
     0,0,0,2,2,0,0,0,
     0,0,0,1,1,0,0,0],
    // F2 = F0 (spider alternates between these two)
    [0,0,0,2,2,0,0,0,
     3,0,2,2,2,2,0,3,
     0,3,2,2,2,2,3,0,
     3,0,0,2,2,0,0,3,
     0,3,0,2,2,0,3,0,
     0,0,0,2,2,0,0,0,
     0,0,0,2,2,0,0,0,
     0,0,0,1,1,0,0,0],
    // F3 = F1
    [0,0,0,2,2,0,0,0,
     0,3,2,2,2,2,3,0,
     3,0,2,2,2,2,0,3,
     0,3,0,2,2,0,3,0,
     3,0,0,2,2,0,0,3,
     0,0,0,2,2,0,0,0,
     0,0,0,2,2,0,0,0,
     0,0,0,1,1,0,0,0],
  ],

  // ══ CHAOSLING ══ fragment of unraveled reality, asymmetric + unstable ══════
  chaosling: [
    // F0 — fragment drift left, left leg (bigger)
    [0,2,2,0,2,0,0,0,
     0,2,1,0,0,2,0,0,
     0,2,2,0,2,2,0,0,
     0,2,2,2,0,2,0,0,
     2,0,2,0,2,0,2,0,
     0,2,0,2,0,2,0,0,
     0,2,3,0,0,3,0,0,
     0,2,2,0,0,0,0,0],
    // F1 — fragment drift right
    [0,0,2,2,0,2,0,0,
     0,2,1,2,0,0,0,0,
     0,0,2,2,0,2,2,0,
     0,0,2,2,2,0,2,0,
     0,2,0,2,0,2,0,0,
     2,0,2,0,2,0,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
    // F2 — fragment spread, right leg (smaller)
    [0,2,2,0,2,0,0,0,
     0,2,1,0,0,2,0,0,
     2,2,2,0,2,0,0,0,
     0,2,2,2,0,2,0,0,
     2,0,2,0,2,0,2,0,
     0,2,0,2,0,2,0,0,
     0,2,3,0,0,3,0,0,
     0,0,0,0,0,2,2,0],
    // F3 = F1
    [0,0,2,2,0,2,0,0,
     0,2,1,2,0,0,0,0,
     0,0,2,2,0,2,2,0,
     0,0,2,2,2,0,2,0,
     0,2,0,2,0,2,0,0,
     2,0,2,0,2,0,0,0,
     0,0,3,0,3,0,0,0,
     0,0,3,0,3,0,0,0],
  ],
};

// Generic fallback for any race not in the map above.
/* prettier-ignore */
const GENERIC_WALK_FRAMES = [
  [0,0,2,2,2,2,0,0,
   0,0,2,1,1,2,0,0,
   0,0,1,1,1,1,0,0,
   0,2,2,2,2,2,2,0,
   0,2,0,2,2,0,2,0,
   0,0,0,2,2,0,0,0,
   0,0,3,0,0,3,0,0,
   0,3,3,0,0,0,0,0],
  [0,0,2,2,2,2,0,0,
   0,0,2,1,1,2,0,0,
   0,0,1,1,1,1,0,0,
   0,2,2,2,2,2,2,0,
   0,0,2,2,2,2,0,0,
   0,0,2,2,2,2,0,0,
   0,0,3,0,3,0,0,0,
   0,0,3,0,3,0,0,0],
  [0,0,2,2,2,2,0,0,
   0,0,2,1,1,2,0,0,
   0,0,1,1,1,1,0,0,
   0,2,2,2,2,2,2,0,
   0,2,0,2,2,0,2,0,
   0,0,0,2,2,0,0,0,
   0,0,3,0,0,3,0,0,
   0,0,0,0,0,3,3,0],
  [0,0,2,2,2,2,0,0,
   0,0,2,1,1,2,0,0,
   0,0,1,1,1,1,0,0,
   0,2,2,2,2,2,2,0,
   0,0,2,2,2,2,0,0,
   0,0,2,2,2,2,0,0,
   0,0,3,0,3,0,0,0,
   0,0,3,0,3,0,0,0],
];

/** Return the 4-frame walk array for a given race id string. */
export function getRaceFrames(raceId) {
  return RACE_WALK_FRAMES[raceId] ?? GENERIC_WALK_FRAMES;
}

// ─────────────────────────── rendering ──────────────────────────────────────

export const SPRITE_DIM = 8;

const _spriteCache = new Map();

/**
 * Render a sprite frame to an HTMLCanvasElement.
 *
 * @param {number[]} frame       - 64-element palette-index array (8×8)
 * @param {string}   charColor   - CSS hex used for palette index 2
 * @param {number}  [scale=5]    - pixel scale factor
 * @param {string}  [accent]     - override for palette index 1 (default parchment)
 * @param {string}  [cacheId]    - optional unique ID to avoid array serialization for cache key
 * @returns {HTMLCanvasElement}
 */
export function renderSprite(frame, charColor, scale = 5, accent = '#f4ead4', cacheId = null) {
  const prefix = cacheId !== null ? cacheId : frame.join(',');
  const cacheKey = `${prefix}_${charColor}_${scale}_${accent}`;
  if (_spriteCache.has(cacheKey)) {
    return _spriteCache.get(cacheKey);
  }

  const size = SPRITE_DIM * scale;
  const canvas = document.createElement('canvas');
  canvas.width  = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  const palette = ['transparent', accent, charColor, _shade(charColor, 0.48)];

  for (let py = 0; py < SPRITE_DIM; py++) {
    for (let px = 0; px < SPRITE_DIM; px++) {
      const idx = frame[py * SPRITE_DIM + px];
      if (idx === 0) continue;
      ctx.fillStyle = palette[idx];
      ctx.fillRect(px * scale, py * scale, scale, scale);
    }
  }

  _spriteCache.set(cacheKey, canvas);
  return canvas;
}

/** Mirror a frame horizontally — used when the character is walking left. */
export function flipH(frame) {
  const out = new Array(SPRITE_DIM * SPRITE_DIM);
  for (let y = 0; y < SPRITE_DIM; y++) {
    for (let x = 0; x < SPRITE_DIM; x++) {
      out[y * SPRITE_DIM + (SPRITE_DIM - 1 - x)] = frame[y * SPRITE_DIM + x];
    }
  }
  return out;
}

function _shade(hex, factor) {
  if (!hex || !hex.startsWith('#') || hex.length < 7) return '#333';
  const r = Math.round(parseInt(hex.slice(1, 3), 16) * factor);
  const g = Math.round(parseInt(hex.slice(3, 5), 16) * factor);
  const b = Math.round(parseInt(hex.slice(5, 7), 16) * factor);
  return `rgb(${r},${g},${b})`;
}
