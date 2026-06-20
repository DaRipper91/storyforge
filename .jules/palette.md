## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2024-06-20 - Decouple :hover and :focus-visible for custom buttons
**Learning:** Grouping `:hover` and `:focus-visible` pseudo-classes on custom UI elements (like `.btn-danger` or `.escape-btn`) causes keyboard focus to improperly trigger mouse-hover visual states (like background color changes) without rendering a clear accessibility focus ring.
**Action:** Always strictly decouple `:hover` and `:focus-visible` selectors, and apply explicit `outline: 2px solid <color>; outline-offset: 2px;` for `:focus-visible` to ensure proper keyboard accessibility without stylistic collision.
