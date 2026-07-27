## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2025-01-20 - Disabled Button Hovers
**Learning:** Disabled elements should never present hover states, as it communicates visual cues of interactivity when none exists.
**Action:** Always append `:not(:disabled)` to button hover classes to ensure disabled states are purely static.
