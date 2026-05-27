## 2023-10-27 - Memoized Sprite Rendering
**Learning:** In a canvas-based grid rendering architecture, re-rendering pixel art sprites frame-by-frame during animation creates a significant number of detached DOM nodes (via `document.createElement('canvas')`) and context operations. The garbage collector pressure causes micro-stutters during walking animations. By memoizing the generated canvases based on frame, color, scale, and accent, we eliminate runtime DOM manipulation and canvas context fetching entirely for repeated frames.
**Action:** Always memoize procedurally generated graphical assets (like customized character sprites) when they are used in high-frequency update loops (like `requestAnimationFrame` or Konva layer updates).

## 2026-05-27 - Preventing Garbage Collection in High-Frequency Canvas Events
**Learning:** Recreating objects like `Konva.Rect` and `Konva.Animation` repeatedly during high-frequency events (e.g., `mousemove`) in the StoryForge canvas renderer causes severe Garbage Collection pressure and micro-stutters. Destroying and appending nodes on every tick is an anti-pattern.
**Action:** For UI elements responding to rapid inputs, instantiate graphical objects (like cursors/glows/animations) once as instance variables and cleanly mutate their properties (x, y, width, height) in the event callback.
