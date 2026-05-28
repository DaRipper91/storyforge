## 2023-10-27 - Memoized Sprite Rendering
**Learning:** In a canvas-based grid rendering architecture, re-rendering pixel art sprites frame-by-frame during animation creates a significant number of detached DOM nodes (via `document.createElement('canvas')`) and context operations. The garbage collector pressure causes micro-stutters during walking animations. By memoizing the generated canvases based on frame, color, scale, and accent, we eliminate runtime DOM manipulation and canvas context fetching entirely for repeated frames.
**Action:** Always memoize procedurally generated graphical assets (like customized character sprites) when they are used in high-frequency update loops (like `requestAnimationFrame` or Konva layer updates).
## 2024-05-23 - Cursor Rendering Optimization
**Learning:** Destroying and recreating Konva nodes or animations within high-frequency event handlers like `mousemove` causes significant garbage collection churn and visual micro-stutters.
**Action:** Always reuse instances of `Konva.Rect` (and similar nodes) and `Konva.Animation`, then mutate their properties on subsequent events rather than instantiating them repeatedly.
