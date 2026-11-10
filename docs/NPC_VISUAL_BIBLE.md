# Feral World NPC Visual Bible

This is the modeling handoff for the Iron Ledge Era cast. It keeps the Godot miniatures, concept sheets, and written lore pointed at the same character.

## Source of truth

Use `docs/WORLD_BIBLE.md`, the NPC prompt files in `src/storyforge/ai/prompts/`, and the seeded descriptions in `data/seeds/default_campaign.json` as canon. The Gemini export supplies additional character-specific appearance notes for D.Anna, Vyra, Bryttan, Evangeline, and Caelyn. Generated turnarounds are modeling references; they do not add new relationships, powers, or story facts.

If a source describes a role but leaves clothing or equipment open, keep the model proposal restrained and label it as an interpretation. Do not turn an attractive generated detail into lore by accident.

## Character directions

| Character | Canonical anchor | Model direction | Confidence |
|---|---|---|---|
| Queen D.Anna (Dee) | Sovereign; ascended Bloodweaver / Solar-Lord hybrid; lover of Kodrik; merciful authority | Crimson and gold regalia, controlled solar light, sovereign scepter and blessing tokens; dark hair from the latest reference sheet | Anchored to reference |
| Vyra Larkholt | Freeblade and traveler; blue Weave axe and lantern in the Gemini export | Layered scout clothing, travel wear, readable axe silhouette and hooded lantern | Anchored to export |
| Bryttan Wolfholt | Wolfguard shieldwarden; slate armor, cobalt wolf crest, power-core pack, blue shard and rune-etched survival dagger | Broad practical armor; keep cobalt details small enough to read on the tabletop token | Anchored to seed and export |
| Evangeline Wolfholt | Young watch scout paired with Bryttan; carries a field codex and lantern in the Gemini export | Shorter slate-and-cobalt field kit; codex, lantern and a small patchwork bunny charm | Role anchored; outfit details interpreted |
| Caelyn Riven | Wayfarer; relic pouch, talisman and rune-touched hand axe in the Gemini export | Slate travel layers, worn pouch, visible talisman and hand axe | Anchored to export |
| Jon | The Store's warm, talkative proprietor; Coco is his companion | Practical shopkeeper layers, apron and ledger; avoid weapons and military armor | Role anchored; clothes interpreted |
| Madame Haylie | Store manager and innkeeper; keeps operational and anomaly ledgers | Capable working clothes with a clear ledger or folio; plum and charcoal are palette proposals | Role anchored; palette interpreted |
| Samael the Ascended | Bored, accurate cosmic and planar lore oracle; loiters at The Store | Understated mage silhouette and worn dark fabrics; visual restraint supports his bored affect | Role anchored; clothes interpreted |
| Cinder Vale | Bard and emotional center of the Crooked Tankard | Stage-ready layers and a portable instrument; use burgundy and muted brass as palette proposals | Role anchored; outfit interpreted |
| Mykael Greenwood | 22-year-old hauler; broad, warm, dark-haired, tribal shoulder tattoo; never a villain | Large human silhouette, work harness, gloves, crates and visible shoulder tattoo; no beast body or combat armor | Anchored to prompt |
| Nathis | Sixteen-year-old tall, slender, fast front man; Tyty is his dog | Age-appropriate light scout clothing, secure boots and small field gear; keep his silhouette lean | Anchored to prompt and bible |
| Coco | Jon and Haylie's chocolate Labrador companion; enthusiastic and food-motivated | Clearly canine anatomy, deep brown coat and practical collar; never give her a combat stat identity | Anchored to bible |
| Tyty | Nathis's long-eared, long-haired dog and loud Wandering Herald | Shaggy hound silhouette, very long ears and simple collar; keep the goofy, companionable read | Anchored to bible |

## Model implementation

- Keep the shared source GLBs untouched. Apply per-instance materials and accessory meshes through `ModelLibrary` appearance passes.
- Use the authored diffuse, normal, and emission maps beside bespoke race GLBs. Match maps to named material surfaces rather than tinting the whole body into a flat color.
- Make age and role visible at the board scale through proportion, equipment, and a restrained palette. A 16-year-old scout should not inherit an adult heavy-armor silhouette; a shopkeeper should not read as a guard.
- Keep all added gear cosmetic. It must not add collision, combat statistics, inventory, or character abilities unless separately authored in the campaign rules.
- Companion animals remain companions and atmosphere. Do not create beast stat blocks, initiative, HP, or combat roles.

## Ironhold environment anchors

The Keep Courtyard is a working fortified yard, not an empty stone rectangle. Preserve the clear route between gates and NPCs while dressing its edges with the seeded supply crates and training equipment. The bronze signal bell on the east wall bracket is the visual focus for **The Quiet Watch** quest; its cracked clapper repeats sounds after dusk. Worn cobbles, iron fittings, wall lanterns, and weathered timber should reinforce daily use without blocking grid movement or obscuring the miniatures.

The throne hall belongs to two stable authorities: D.Anna governs the Crown and Kodrik leads the Iron Ledge Company. Keep their regalia and banners distinct; their partnership is settled lore, never a source of conflict or leverage.
