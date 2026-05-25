## 2024-11-20 - Ensure Semantic Form Relationships
**Learning:** Found several instances where pseudo-labels (using `<span>` or `<p>` tags) were used next to inputs without proper semantic `<label>` grouping or `id` mapping. Also, dynamic inputs (e.g., custom pronoun or title inputs) lacked ARIA labels, which degrades screen reader accessibility.
**Action:** When working on form inputs, always use semantic `<label>` tags linked via `for`/`htmlFor` and `id`, or use `aria-label` for inputs that inherently do not have visible labels to maintain full accessibility.
