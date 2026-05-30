## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.
## 2024-05-24 - Enhance keyboard focus states with :focus-visible
**Learning:** Replaced `:focus` with `:focus-visible` across buttons (`.btn`, `.menu-options button`) to eliminate sticky focus rings after mouse clicks while retaining them for keyboard navigation. This is a highly reusable UX pattern for this design system.
**Action:** Default to using `:focus-visible` instead of `:focus` for all interactive components (buttons, modals) in future UI additions.
