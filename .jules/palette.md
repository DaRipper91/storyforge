## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2026-06-24 - Dynamic Form Element Accessibility
**Learning:** When generating complex form UI dynamically via vanilla JavaScript (like `document.createElement()`), standard accessibility associations are easily missed. Specifically, `<label>` elements will not automatically associate with their corresponding `<input>` or `<textarea>` unless `htmlFor` and `id` properties are explicitly set during creation.
**Action:** When reviewing dynamically generated UI code, proactively verify that all form controls have corresponding explicitly associated labels via `id`/`htmlFor`, or fallback to `aria-label` when a visible label is intentionally omitted (e.g., in a lobby slot card).
