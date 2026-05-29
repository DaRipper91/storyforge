## 2023-10-27 - Memoized Sprite Rendering
**Learning:** In a canvas-based grid rendering architecture, re-rendering pixel art sprites frame-by-frame during animation creates a significant number of detached DOM nodes (via `document.createElement('canvas')`) and context operations. The garbage collector pressure causes micro-stutters during walking animations. By memoizing the generated canvases based on frame, color, scale, and accent, we eliminate runtime DOM manipulation and canvas context fetching entirely for repeated frames.
**Action:** Always memoize procedurally generated graphical assets (like customized character sprites) when they are used in high-frequency update loops (like `requestAnimationFrame` or Konva layer updates).

## 2026-05-29 - [Konva Mousemove Garbage Collection]
**Learning:** [Destroying and recreating Konva layers or Canvas nodes on high-frequency events (like `mousemove` during cursor rendering) creates severe Garbage Collection pressure and micro-stutters. Creating objects like Konva.Circle and Konva.Tween inside a mousemove handler instead of instantiating them once and mutating them causes significant rendering overhead.]
**Action:** [Optimize by instantiating graphics objects once and mutating their properties (e.g. `node.position()`, `tween.play()`) during the event loop instead of recreating them.]
