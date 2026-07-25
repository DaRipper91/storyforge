## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2024-07-23 - Prevent interactive styles on disabled buttons
**Learning:** Disabled elements should not show hover or focus-visible interactivity cues, as this falsely indicates to the user (especially mouse/keyboard users) that the element can be interacted with.
**Action:** When styling interactive elements, always chain `:hover` and `:focus-visible` pseudo-classes with `:not(:disabled)` (e.g., `.btn:hover:not(:disabled)`) to ensure that disabled elements do not falsely indicate interactivity. Add a base `.btn:disabled` state to ensure consistent visual disabled state across all buttons (reduced opacity, cursor not-allowed).
