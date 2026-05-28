## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2024-05-24 - Global Disabled Button States
**Learning:** Found that multiple components (like `.jon-item-buy` and `.escape-btn`) were being programmatically disabled via JavaScript (`btn.disabled = true`) but lacked corresponding visual CSS styles. This caused disabled buttons to still look interactive and trigger hover effects, leading to confusing UX.
**Action:** Implemented a global `button:disabled, .btn:disabled` CSS rule in `styles.css` to consistently reduce opacity, remove hover effects (transform/box-shadow/filter), and apply `cursor: not-allowed` across all buttons.
