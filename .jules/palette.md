## 2024-04-20 - Sticky Focus Rings
**Learning:** Grouping `:hover` and `:focus` (or omitting outline on focus) creates "sticky" focus rings after mouse clicks, confusing mouse users while hurting keyboard navigation.
**Action:** Always decouple `:hover` and `:focus-visible`. Use `:focus-visible` with a distinct `outline` for keyboard users, separate from mouse-driven `:hover` state.

## 2024-07-22 - Visual clarity for disabled buttons
**Learning:** Disabled interactive elements (buttons, custom UI controls) must not trigger hover or focus states, as this falsely implies interactivity. Furthermore, CSS `pointer-events: none` on an element prevents the `cursor: not-allowed` rule from displaying on that same element.
**Action:** When styling interactive elements, always chain `:hover` and `:focus-visible` pseudo-classes with `:not(:disabled)` (e.g., `.btn:hover:not(:disabled)`). If you need a `not-allowed` cursor on a disabled element, you may need to reconsider using `pointer-events: none`, or accept that the cursor won't show if the pointer events are blocked.
