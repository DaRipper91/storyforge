## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2024-05-18 - Missing label connections for dynamically created inputs
**Learning:** When using `document.createElement` to generate UI forms dynamically in pure JS (like the character creator in `lobby.js`), standard HTML semantic practices are easily forgotten. We created `<label>`s but did not link them to `<textarea>`s and `<input>`s with `htmlFor` and `id`, preventing screen readers from associating the prompt with the field.
**Action:** When dynamically creating form fields, explicitly set `label.htmlFor = "some-id"` and `input.id = "some-id"`. If a visible label breaks layout or design, ensure an `aria-label` is provided on the input element itself.
