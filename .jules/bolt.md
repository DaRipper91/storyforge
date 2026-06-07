## 2025-02-28 - Throttle high-frequency event listeners

**Learning:** High-frequency DOM events (like `mousemove` or `scroll`) that trigger timer resets (`clearTimeout` and `setTimeout`) can cause excessive micro-allocations and severe Garbage Collection churn, leading to frame drops.
**Action:** Always throttle or debounce handlers tied to high-frequency events, especially when they instantiate timers or objects, even if the actual business logic inside seems lightweight.
