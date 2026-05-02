# Echofy — HTML snippets and static build

**When to read this:** Changing page layout, copy, or structure in the static frontend.

## Rule of thumb

**Edit snippets, not hand-edit built HTML** — unless you are fixing a one-off and will immediately reconcile with snippets.

## Layout

| Area | Path |
|------|------|
| Page shell top | `frontend/snippets/layout-top.html` (`{{PAGE_TITLE}}` placeholder) |
| Main content | `frontend/snippets/bodies/<page>.html` |
| Footer / bottom | `frontend/snippets/footers/<page>.html` |
| Built output | `frontend/public/*.html` |

Which pages exist and which JS files load are defined in **`scripts/render_static_html.py`** (`PAGES` list).

## Regenerate `public/*.html`

From **repo root**:

```bash
python scripts/render_static_html.py
```

Commit the updated files under `frontend/public/` (e.g. `index.html`, `discover.html`).

## CI

The Static Web Apps workflow runs the same render step before deploy — keep snippets and `PAGES` in sync so CI output matches local.

## Assets

- Shared JS: `frontend/public/js/`
- CSS: `frontend/public/css/`

Changes to **only** `js/` or `css/` do not require the render script unless HTML references new files.
