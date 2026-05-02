# Echofy — agent instructions (Cursor)

## Session start (required)

1. **Understand the project before editing code.** Read the project orientation markdown first — at minimum skim `overview.md`, then open any other files needed from the skill folders listed below.
2. **Only dive into source files** (`backend/`, `frontend/`, `scripts/`, etc.) when the docs are insufficient or you are implementing a concrete change.

### Where the docs live (same content, mirrored)

| Location | Notes |
|----------|--------|
| `.cursor/skills/` | Cursor-oriented copy |
| `.agents/` | General agent copy |
| `.claude/skills/` | Claude Code copy (create if missing) |
| `.codex/skills/` | Codex-oriented copy (create folder if missing) |

Files to use as the map of the system include: `overview.md`, `frontend.md`, `backend.md`, `api.md`, `security.md`, `database.md`, `spotify_api.md`, `deployment.md`, `integrations.md`.

Authoritative env and human setup: `.env.example`, `README.md`.

## After important changes (required)

When you make **material** changes — for example **new UI/design**, **backend logic or routes**, **database schema or models**, **Spotify/API behavior**, **auth or security**, **deployment or integrations** — you **must**:

1. **Update** the affected markdown in **one canonical place** (prefer **`.cursor/skills/`**), so facts match the codebase.
2. **Copy the updated `.md` files** so all mirrors stay identical:
   - `.cursor/skills/*.md` → `.agents/`
   - `.cursor/skills/*.md` → `.claude/skills/` (create `skills` if needed)
   - `.cursor/skills/*.md` → `.codex/skills/` (create `skills` if needed)

If you only edited a mirror by mistake, reconcile so all four locations match before finishing the task.

## Copy command (repo root, PowerShell)

```powershell
$src = ".\.cursor\skills\*.md"
Copy-Item $src ".\.agents\" -Force
New-Item -ItemType Directory -Force ".\.claude\skills" | Out-Null
Copy-Item $src ".\.claude\skills\" -Force
New-Item -ItemType Directory -Force ".\.codex\skills" | Out-Null
Copy-Item $src ".\.codex\skills\" -Force
```

Adjust paths on macOS/Linux (`cp .cursor/skills/*.md .agents/` etc.) as needed.
