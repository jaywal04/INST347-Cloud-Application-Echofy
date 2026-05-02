# Echofy — agent instructions (Claude Code)

## Session start (required)

1. **Understand the project before editing code.** Read the orientation markdown in the skill folders first — at minimum `overview.md`, then any other `*.md` needed for the task (`api.md`, `backend.md`, `database.md`, etc.).
2. **Use the codebase** only when you need detail beyond the docs, or when implementing changes.

### Mirrored doc roots (keep in sync; same filenames)

| Path | Purpose |
|------|---------|
| `.cursor/skills/` | Preferred **canonical** copy to edit |
| `.agents/` | Mirrored project docs |
| `.claude/skills/` | This ecosystem’s copy |
| `.codex/skills/` | Codex copy (create if absent) |

Typical files: `overview.md`, `frontend.md`, `backend.md`, `api.md`, `security.md`, `database.md`, `spotify_api.md`, `deployment.md`, `integrations.md`.

Also see: `README.md`, `.env.example`.

## After important changes (required)

For **substantive** work — **new design/UI**, **backend or API behavior**, **database/models/migrations**, **Spotify or external integrations**, **auth/session/security**, **deploy/CI** — you **must**:

1. **Update** the relevant `*.md` under **`.cursor/skills/`** (canonical).
2. **Propagate** every changed file to: **`.agents/`**, **`.claude/skills/`**, and **`.codex/skills/`** so all copies match.

Do not leave mirrors stale after a significant change.

## One-shot sync from repo root (bash)

```bash
mkdir -p .claude/skills .codex/skills
cp .cursor/skills/*.md .agents/
cp .cursor/skills/*.md .claude/skills/
cp .cursor/skills/*.md .codex/skills/
```

On Windows PowerShell, use the copy block in `AGENTS.md` or equivalent `Copy-Item` commands.
