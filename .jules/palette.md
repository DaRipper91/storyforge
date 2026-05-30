## 2026-05-30 - Prevent sticky focus on buttons
**Learning:** Using `:focus` on buttons causes the focus ring to remain "stuck" after a mouse click, which can be visually confusing or unappealing for mouse users. Keyboard users, however, still need visible focus indicators to navigate the UI.
**Action:** Replace `:focus` with `:focus-visible` on interactive elements like buttons. This ensures the focus ring is only shown when navigating with a keyboard, providing a clean experience for mouse users while preserving accessibility.
