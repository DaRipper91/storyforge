## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2026-05-24 - Form Input Labeling
**Learning:** Adding `label for="..."` tags to sliders and adding `aria-labelledby` attributes to text inputs improves keyboard and screen-reader accessibility for setting controls and modal inputs.
**Action:** Always ensure that form inputs have a clear labeling association, particularly for custom slider setups or text inputs that lack a traditional label.
