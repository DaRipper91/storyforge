## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2024-07-03 - Dynamic Form Accessibility
**Learning:** The application extensively uses vanilla JS `document.createElement()` to build complex forms (like character creation), frequently resulting in `<label>` and `<input>`/`<textarea>` elements that are visually grouped but lack programmatic association for screen readers.
**Action:** When creating form elements dynamically, always explicitly assign matching `id` and `htmlFor` properties to maintain strict a11y compliance.
