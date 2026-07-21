## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2024-05-24 - Focus Visibility on Range Inputs
**Learning:** Using `-webkit-appearance: none` and `outline: none` on range inputs `<input type="range">` removes the native browser focus ring, creating a severe accessibility issue for keyboard users who cannot see which slider is focused.
**Action:** Always ensure a custom `:focus-visible` state with a clear outline or border is implemented when overriding native input styling, especially for range sliders.
