## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2026-05-27 - Custom Button Focus Accessibility
**Learning:** Found that custom button classes (`.btn`, `.menu-btn`, `.escape-btn`) were missing keyboard `:focus-visible` styling, which hurt keyboard navigation accessibility. Ensuring a uniform visual focus state (e.g., `outline: 2px solid var(--ink-gilded); outline-offset: 2px;`) across custom components is crucial for screen reader users and those unable to use a mouse.
**Action:** When implementing custom button classes in the design system, always explicitly define a `:focus-visible` style to maintain WCAG accessibility for keyboard users.
