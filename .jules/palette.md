## 2024-06-02 - Focus Visibility in Hybrid Apps
**Learning:** In desktop-like web apps (using PyWebView), relying strictly on `:focus` causes annoying sticky outlines when users click buttons with a mouse. The `:focus-visible` pseudo-class correctly distinguishes between keyboard tabbing and mouse clicks, preventing visual clutter while maintaining full accessibility.
**Action:** Default to using `:focus-visible` instead of `:focus` for all interactive elements across the platform unless explicit focus persistence is required.
