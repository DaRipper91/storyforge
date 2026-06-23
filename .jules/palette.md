## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2026-06-23 - Vanilla JS Dynamic Elements Accessibility
**Learning:** Dynamically created vanilla JavaScript form elements (using `document.createElement`) often lack explicit `id` and `htmlFor` attributes, which severs the connection between a `<label>` and its corresponding `<input>` or `<textarea>` for screen readers.
**Action:** Always assign a unique `id` to the input element and assign the exact same string to the `htmlFor` property of the label element when creating them dynamically.
