## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2024-04-20 - Standardize Button Disabled States
**Learning:** Hardcoding `:disabled` states with specific IDs or extra classes creates redundancy and brittle CSS. It's better to explicitly add a base `.btn:disabled` state and selectively decouple interactive behaviors from it.
**Action:** Always decouple interactive states (like `:hover` and `:focus-visible`) from disabled states using `:not(:disabled)` on the base `.btn` class.
