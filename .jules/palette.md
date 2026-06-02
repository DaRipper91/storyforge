## 2026-06-02 - Focus Visibility and Sticky Rings
**Learning:** Using standard `:focus` styles on interactive components (especially custom buttons) causes "sticky" focus rings to appear when users click on them with a mouse, which can look unintended or broken.
**Action:** Use `:focus-visible` instead of `:focus` for focus indicators. This preserves the focus ring for keyboard navigation while eliminating it for mouse interactions, creating a cleaner experience without compromising accessibility.
