# Dynamic World Maps (Before/After Paradox) Design

## Overview
To transition *StoryForge* from a simple virtual tabletop game towards a thematic, lore-rich action RPG in the vein of *Diablo 2*, we have integrated custom map visual assets to represent the timeline shift caused by the Weaver's Paradox in the Feral World.

The game features two world maps:
1. **Before Paradox Map** (`map1.png` on disk) - The world in its original, civilized state.
2. **After Paradox Map** (`map2.png` on disk) - The world in its post-paradox, feral state.

## Implementation Details

### Asset Placement
* Source assets: `/home/daripper/Projects/storyforge/map1.png` and `/home/daripper/Projects/storyforge/map2.png`
* Destination assets: `res://assets/textures/map1.png` and `res://assets/textures/map2.png` (within the Godot import directory).

### Client Integration (`Tabletop.gd`)
1. **Texture Rect Instantiation**: We introduced `_map_texture_rect` (a `TextureRect` node) in the world map Control container to serve as the background layer for the fast travel map.
2. **Dynamic Era Parsing**: The game client retrieves the campaign's `era` field (which contains either `before` or `after` based on the campaign model) from the server's campaign state.
3. **Texture Swapping**: We implemented `_update_world_map_texture(era: String)` to dynamically load and assign the appropriate high-resolution texture:
   - `res://assets/textures/map1.png` for `"before"`.
   - `res://assets/textures/map2.png` for `"after"`.
4. **State synchronization**: Whenever `_on_state_updated()` is triggered by the backend, the client re-evaluates the era and swaps the texture seamlessly.

## Visual Polish
* The map texture rect is modulated to `Color(1, 1, 1, 0.85)` to keep fast travel node connection lines and button labels fully legible.
* It leverages `STRETCH_SCALE` and `EXPAND_IGNORE_SIZE` to fit the central travel map frame perfectly, aligning with the current node positions (`WORLD_MAP_NODES`).
