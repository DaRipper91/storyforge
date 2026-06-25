## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2024-06-25 - Form Labels in Vanilla JS
**Learning:** Dynamically created complex forms via `document.createElement()` (like the Character Creation process) often miss explicit `id` and `htmlFor` bindings between inputs and labels, causing screen reader failures.
**Action:** When dynamically generating inputs with corresponding descriptive text, always generate paired IDs and explicitly set `label.htmlFor` to ensure accessibility is maintained programmatically.
