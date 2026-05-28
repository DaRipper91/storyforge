## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.
## 2023-10-25 - Prevent Sticky Focus States on Clicks
**Learning:** This application extensively relies on custom UI components like buttons and modal inputs, which suffered from "sticky" focus styles when using `:focus` because mouse clicks trigger focus.
**Action:** Replace `:focus` with `:focus-visible` to ensure focus rings/styles only appear during keyboard navigation, while maintaining `:hover` for pointer interactions. Apply clear `outline` and `outline-offset` to all `:focus-visible` states to improve a11y for keyboard users without degrading mouse UX.
