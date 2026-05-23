# Shimmering Thresher: Visual Implementation Strategy

**Status**: Atmospheric Beast / Non-Mechanical Entity  
**Rendering Style**: 2.5D Cinematic (3D Node in 2D-Parallax Environment)

## 🏛️ Node Structure (Godot 4.x)
- **Root (Node3D)**: `ShimmeringThresher`
    - **Body (MeshInstance3D)**: A highly-subdivided Plane or Ribbon mesh. 
        - *Rationale*: Allows for smooth vertex-based undulation that a standard Sprite3D cannot achieve.
    - **Mist Trail (GPUParticles3D)**: High-density, low-lifespan particles.
        - *Visuals*: Translucent, oil-slick tinted flakes that "shed" from the body as it moves.
    - **Heat Distortion (MeshInstance3D)**: A slightly larger, invisible plane following the body.
        - *Purpose*: Hosts the Screen-Reading shader for the mirage effect.
    - **AnimationPlayer**: For global floating loops and transformation tweens.

## 🎨 Shader Approach

### 1. The Iridescent Membrane (Spatial Shader)
- **Fresnel Effect**: Use `1.0 - dot(NORMAL, VIEW)` to create a glow at the edges.
- **Color Mapping**: Map the Fresnel result and a secondary Voronoi noise to a `GradientTexture1D` containing the "oil-slick rainbow" spectrum (Cyan, Magenta, Gold, Deep Violet).
- **Alpha Blending**: Set `Transparency` to `Mix`. Use a scrolling noise texture to create "thin" and "thick" spots in the membrane.

### 2. Geometric Heat Mirage (Screen-Reading Shader)
- **Screen Texture**: Capture `SCREEN_TEXTURE` at the beast's location.
- **Distortion**: Apply UV offsets based on a sharp, "micro-serrated" noise map (using a stepped function on a perlin noise to make it feel geometric/crystalline rather than organic).
- **Edge Sharpness**: Use a high-contrast Normal map on the Mesh to catch light like shards of glass.

## 🏃 Movement & Animation
- **Liquid Undulation**: Controlled via Vertex Shader. 
    - `VERTEX.y += sin(VERTEX.x * 2.0 + TIME * 3.0) * amplitude;`
    - This creates the "ribbon-like" swimming motion without needing a complex bone rig.
- **Vertical Oscillation**: A slow, sine-wave vertical float (0.5m range) applied via `AnimationPlayer` to give a sense of weightless hovering.
- **Pathing**: Use `Tween` to move the Root node between anchor points in the Sunless Canyons. Movement should be slow and deliberate, turning with wide, sweeping arcs.

## 🚫 Mechanical UI Mandate
- **No HUD Elements**: No health bars, level indicators, or nameplates.
- **No Selection Logic**: The entity does not react to mouse-over or targeting. 
- **Environmental Interaction Only**: If a player moves through it, the heat mirage shader should simply distort the player's sprite, emphasizing its role as a "living hazard" and atmospheric set-piece rather than a combatant.
