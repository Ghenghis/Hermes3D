# h3dos-wire-learning-topics

- **UI surface**: Learning topic cards in `#learningTopics` (selectors: `.setup-card, .topic-card, .learning-card, article`)
- **Tab**: Learning
- **Backend endpoint**: `POST /api/learning/bookmark` — Action Window primary action "Bookmark"
  - Panels show "Linked Papers" data already loaded with the topic; no separate fetch wired in this slot
- **Files changed** (PR #39, commit `7985de0`):
  - `apps/web/app.js` — +23 lines (Slot 11: topic card click → ActionWindow `kind=topic`, Linked Papers panel)
  - `tests/e2e/wire-learning-topics-actionwindow.spec.ts` — +27 lines (handles 0-cards gracefully)
- **Status**: MERGED (PR #39 in branch log); this worktree carries cascade re-resolves
- **Branch & last commit**: `wire/learning-topics-actionwindow` @ `39cbf28 merge(develop): cascade re-resolve — re-append learning topics AW handler`
- **Path**: `G:\Github\h3dos-wire-learning-topics`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#fb923c; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#fb923c; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#fb923c"/></marker></defs>
  <rect class="box" x="10" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="20" y="62">#learningTopics</text>
  <text class="small" x="20" y="80">.topic-card</text>
  <text class="small" x="20" y="95">click</text>
  <path class="arrow" d="M130,70 L170,70"/>
  <rect class="box" x="170" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="180" y="62">ActionWindow</text>
  <text class="small" x="180" y="80">kind=topic</text>
  <text class="small" x="180" y="95">+Linked Papers panel</text>
  <path class="arrow" d="M290,70 L330,70"/>
  <rect class="box" x="330" y="40" width="65" height="60" rx="6"/>
  <text class="small" x="338" y="62">POST</text>
  <text class="small" x="338" y="78">/api/</text>
  <text class="small" x="338" y="92">learning/</text>
  <text class="small" x="338" y="106">bookmark</text>
  <rect class="box" x="80" y="160" width="240" height="60" rx="6"/>
  <text class="label" x="92" y="185">Response: { ok: true, bookmark_id }</text>
  <text class="small" x="92" y="205">Panel data is local (Linked Papers from card)</text>
</svg>
```
