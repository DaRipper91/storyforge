## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2024-05-26 - Dynamic Content Accessibility
**Learning:** For Virtual Tabletop (VTT) web applications, dynamic game logs and narrative elements (like an event log or chat) need to be automatically announced to screen readers. Adding `aria-live="polite"` to elements like `<ol id="narrative-log">` ensures screen reader users can passively track the game state without having to manually navigate back to the log after every action.
**Action:** Always use `aria-live` on containers that receive continuous appended updates crucial to the primary user experience.
