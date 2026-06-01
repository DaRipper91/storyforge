## 2024-06-01 - [Better Focus States]
**Learning:** Using `:focus` on buttons creates 'sticky' focus rings after a mouse click, causing confusion for mouse users. Switching to `:focus-visible` ensures that focus indicators only appear when a user is navigating via keyboard.
**Action:** Always prefer `:focus-visible` over `:focus` for UI components (buttons, modals) to guarantee a clean experience for mouse users while preserving accessibility for keyboard users.
