## 2026-05-25 - Canvas GC Churn in Animation Loops
**Learning:** Recreating `<canvas>` elements for every frame during a sprite animation creates massive garbage collection churn that manifests as micro-stutters during walks. This codebase frequently re-renders small pixel art elements.
**Action:** Memoize generated `canvas` objects using their array reference as a key. This pattern significantly reduces GC load for static or repeating pixel art like walk cycles.
