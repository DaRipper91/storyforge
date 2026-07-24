## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2024-05-15 - Dynamic Form Accessibility (Vanilla JS)
**Learning:** When generating form UI components dynamically via vanilla JavaScript (e.g., `document.createElement()`), standard HTML accessibility associations are often lost.
**Action:** Always explicitly set the `id` property on inputs or textareas, and the `htmlFor` property on their corresponding `<label>` elements to ensure proper screen reader support, or use `aria-label` as a fallback. When replacing block-level semantic elements (like `<p>`) with inline-level elements (like `<label>`), ensure the CSS is updated with `display: block;` to preserve layout.
