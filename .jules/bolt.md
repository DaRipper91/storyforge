## 2023-10-27 - Memoized Sprite Rendering
**Learning:** In a canvas-based grid rendering architecture, re-rendering pixel art sprites frame-by-frame during animation creates a significant number of detached DOM nodes (via `document.createElement('canvas')`) and context operations. The garbage collector pressure causes micro-stutters during walking animations. By memoizing the generated canvases based on frame, color, scale, and accent, we eliminate runtime DOM manipulation and canvas context fetching entirely for repeated frames.
**Action:** Always memoize procedurally generated graphical assets (like customized character sprites) when they are used in high-frequency update loops (like `requestAnimationFrame` or Konva layer updates).
## 2024-05-19 - Avoid Recreating Konva Graphics on High-Frequency Events
**Learning:** Destroying and recreating Konva layers or Canvas nodes on high-frequency events (e.g., `mousemove` causing cursor position updates) creates severe Garbage Collection pressure and micro-stutters.
**Action:** Optimize by instantiating graphics objects and animations once and mutating their properties (like `x`, `y`, `width`, `height`, or `setAttrs`) during the event loop instead of destroying and recreating them.
## 2024-06-16 - Throttle High-Frequency Events
**Learning:** High-frequency DOM events (like `mousemove`) that continuously trigger timer operations (`clearTimeout` and `setTimeout`) cause unnecessary micro-allocations and severe Garbage Collection churn. Throttling these resets significantly reduces CPU overhead.
**Action:** When throttling high-frequency events in JavaScript to prevent GC churn, prefer a timestamp-based approach (e.g., using `Date.now()`) over creating additional timers with `setTimeout`, as `setTimeout` still inherently allocates memory for callbacks and internal V8 structures.
## 2024-07-28 - Explicitly Stop Konva Animations
**Learning:** When reusing graphical animation loops (like `Konva.Animation`) or destroying parent nodes, failing to explicitly call `.stop()` causes the animation to continue executing in the background infinitely. This results in unnecessary CPU cycles being burned and prevents the Garbage Collector from cleaning up detached nodes, causing memory leaks.
**Action:** Always explicitly call `.stop()` on Konva Animations when their parent components/layers are hidden, unmounted, or destroyed.
