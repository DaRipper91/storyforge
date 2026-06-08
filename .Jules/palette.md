## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2024-05-26 - Dynamic Content Accessibility
**Learning:** For Virtual Tabletop (VTT) web applications, dynamic game logs and narrative elements (like an event log or chat) need to be automatically announced to screen readers. Adding `aria-live="polite"` to elements like `<ol id="narrative-log">` ensures screen reader users can passively track the game state without having to manually navigate back to the log after every action.
**Action:** Always use `aria-live` on containers that receive continuous appended updates crucial to the primary user experience.

## 2024-05-27 - Focus Styles vs Hover Styles
**Learning:** When styling interactive elements like buttons and sliders, do not group `:hover` and `:focus-visible` pseudo-class selectors together if they require different visual behaviors. Decoupling them and using explicit `outline` and `outline-offset` for `:focus-visible` prevents the hover state from unintentionally inheriting focus-specific styles, ensuring a cleaner experience for mouse users while preserving strong visual indicators for keyboard navigation.
**Action:** Always write separate CSS rules for `:hover` and `:focus-visible` unless the visual presentation should be strictly identical for both pointer and keyboard interactions.
