## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.
## 2024-06-16 - Maintain Contrast for Focus Rings on Dark Backgrounds
**Learning:** While the standard focus outline color (`var(--ink-midnight)`) works well for most buttons in the application, interactive elements nested inside dark containers (such as `.jon-action-panel` modals) suffer from poor visibility with this dark outline, violating WCAG contrast rules for keyboard navigation.
**Action:** When adding `:focus-visible` styles to elements on dark backgrounds (like `.escape-btn`), explicitly override the outline color to a lighter theme token (e.g., `var(--ink-gilded)`) to ensure sufficient contrast.
