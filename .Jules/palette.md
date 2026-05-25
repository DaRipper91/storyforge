## 2024-05-23 - Minimize Button Accessibility
**Learning:** Added `aria-label="Minimize Window"` to the app menu minimize button. Found that adding `aria-label` to buttons that already have clear descriptive text (e.g. "Settings", "Quit") is an accessibility anti-pattern because it's redundant. `aria-label` should only be used when visible text is missing or insufficient (like the "—" button).
**Action:** Only use `aria-label` on buttons that are icon-only or have text that doesn't fully explain their action.

## 2026-05-25 - Modal and Custom Range Slider Accessibility
**Learning:** Custom UI components like modals and range sliders require explicit ARIA and HTML attribute mapping for screen readers. In `index.html`, textareas need `aria-labelledby` linked to the modal's heading and `aria-describedby` linked to hint text. Custom `div` wrappers acting as labels for range inputs must be converted to proper `<label for="[id]">` tags to ensure the slider context is announced correctly.
**Action:** When creating or modifying custom dialogs and input sliders, always ensure inputs are explicitly tied to their descriptive text using `aria-labelledby`/`aria-describedby` or semantic `<label>` elements.
