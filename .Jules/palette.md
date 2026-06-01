## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2024-06-25 - Focus Visible for Interactive Elements
**Learning:** Using `:focus` on interactive elements like buttons and inputs causes "sticky" focus styles to remain active after a mouse click, degrading the visual experience. Found that using `:focus-visible` ensures that focus indicators are only shown when navigating via keyboard, keeping the mouse interaction clean while maintaining accessibility.
**Action:** Always use `:focus-visible` instead of `:focus` when applying focus rings or active state styles to interactive elements like buttons, cards, and inputs.
