## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2024-06-06 - Missing focus states on custom list action buttons
**Learning:** Many interactive list items/action buttons like `.escape-btn` in the lobby UI were dynamically generated and had custom `:hover` states but no `:focus-visible` states, breaking keyboard accessibility for primary actions.
**Action:** When adding or discovering custom stylized UI buttons (especially `.escape-btn`, `.samael-consult-btns`, `.keeva-action-btns`), decouple their `:hover` and `:focus-visible` pseudo-classes to ensure focus states are clearly visible for keyboard users.
