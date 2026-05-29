## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2024-05-29 - Interactive Elements Keyboard vs Mouse Focus
**Learning:** This app's interactive elements heavily rely on `:focus` styling that triggers a "sticky" focus ring when clicked with a mouse. This is a common pattern that causes cognitive load and a lingering ring after a mouse action, but keyboard navigation fully relies on it. Replacing `:focus` with `:focus-visible` (and adding it wherever `:hover` applies to ensure consistency for keyboard users) immediately solves the sticky click issue while fully preserving tab navigation support.
**Action:** Always prefer `:focus-visible` over `:focus` for button/menu elements to prevent sticky interactions for pointer users without abandoning keyboard users.
