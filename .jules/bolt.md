## 2023-10-27 - Memoized Sprite Rendering
**Learning:** In a canvas-based grid rendering architecture, re-rendering pixel art sprites frame-by-frame during animation creates a significant number of detached DOM nodes (via `document.createElement('canvas')`) and context operations. The garbage collector pressure causes micro-stutters during walking animations. By memoizing the generated canvases based on frame, color, scale, and accent, we eliminate runtime DOM manipulation and canvas context fetching entirely for repeated frames.
**Action:** Always memoize procedurally generated graphical assets (like customized character sprites) when they are used in high-frequency update loops (like `requestAnimationFrame` or Konva layer updates).

## 2024-05-20 - Memoizing Render Objects on High-Frequency Events
**Learning:** Destroying and recreating Konva layers or Canvas nodes on high-frequency events (e.g., `mousemove`) creates severe Garbage Collection pressure and micro-stutters.
**Action:** Optimize by instantiating graphics objects once and mutating their properties during the event loop.
