## 2023-10-27 - Memoized Sprite Rendering
**Learning:** In a canvas-based grid rendering architecture, re-rendering pixel art sprites frame-by-frame during animation creates a significant number of detached DOM nodes (via `document.createElement('canvas')`) and context operations. The garbage collector pressure causes micro-stutters during walking animations. By memoizing the generated canvases based on frame, color, scale, and accent, we eliminate runtime DOM manipulation and canvas context fetching entirely for repeated frames.
**Action:** Always memoize procedurally generated graphical assets (like customized character sprites) when they are used in high-frequency update loops (like `requestAnimationFrame` or Konva layer updates).

## 2024-05-20 - Avoid destroying Konva nodes in high-frequency event handlers
**Learning:** Recreating Konva nodes (e.g., `destroyChildren()` and creating new `Konva.Rect`s or animations) inside high-frequency handlers like cursor navigation (`mousemove`) generates excessive Garbage Collection pressure, causing severe micro-stutters during gameplay.
**Action:** Always extract Konva object creation to initialize exactly once, then dynamically update positions, widths, or colors during the object's `Konva.Animation` frame loop using instance properties like `this.cursor`.
