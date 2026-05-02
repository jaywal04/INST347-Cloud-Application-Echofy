# Echofy — agent instructions (Cursor)

## Session start (required)

1. **Understand the project before editing code.** Read the orientation markdown in the **skills** folders first — at minimum skim **`overview.md`**, then **`class-project.md`** and **`local-dev.md`** if you will run or change the app; open other `*.md` as needed (`api.md`, `backend.md`, etc.).
2. **Only dive into source files** (`backend/`, `frontend/`, `scripts/`, etc.) when the docs are insufficient or you are implementing a concrete change.

### Where the docs live (same content, mirrored)

| Location | Notes |
|----------|--------|
| `.cursor/skills/` | **Canonical** copy — edit here first |
| `.agents/skills/` | Mirrored project docs |
| `.claude/skills/` | Claude Code copy (create if missing) |
| `.codex/skills/` | Codex copy (create folder if missing) |

Authoritative env and human setup: `.env.example`, `README.md`.

## Database changes and production compatibility (required)

Any change to the **database schema** (new tables, new columns, new indexes or constraints, renamed semantics) **must remain compatible with older databases** that already exist in production or on teammates’ machines after `git pull`.

1. **Never assume a green-field DB only.** After commit and deploy, the live database may still be on an older shape until the app runs its startup path (or until you add an explicit migration). Users must not hit crashes or `OperationalError` / missing-column failures when they use a feature that depends on the new schema.
2. **Ship the upgrade path in code** for this project: extend **`backend/app/schema_sync.py`** (and/or rely on `db.create_all()` for *new* tables) so that at **app startup** the deployed database is brought in line—e.g. missing columns added, legacy duplicates cleaned before unique indexes, new tables created. Register new models in the sync loop where appropriate.
3. **Prefer additive, nullable, or defaulted columns** when possible so old rows remain valid; avoid breaking renames without a transitional step documented in **`.cursor/skills/database.md`**.
4. **Document** the change in **`.cursor/skills/database.md`** (and mirror per below) so agents and humans know what was added and how existing DBs are upgraded.

Details and examples: **`.cursor/skills/database.md`** → *Backward-compatible schema changes*.

## After important changes (required)

When you make **material** changes — for example **new UI/design**, **backend logic or routes**, **database schema or models**, **Spotify/API behavior**, **auth or security**, **deployment or integrations**, **HTML snippet workflow or `PAGES` list** — you **must**:

1. **Update** the affected `*.md` under **`.cursor/skills/`** so facts match the codebase.
2. **Copy** all skill markdown to the mirrors so they stay identical:
   - `.cursor/skills/*.md` → `.agents/skills/`
   - `.cursor/skills/*.md` → `.claude/skills/`
   - `.cursor/skills/*.md` → `.codex/skills/`

## Copy command (repo root, PowerShell)

```powershell
$src = ".\.cursor\skills\*.md"
New-Item -ItemType Directory -Force ".\.agents\skills" | Out-Null
Copy-Item $src ".\.agents\skills\" -Force
New-Item -ItemType Directory -Force ".\.claude\skills" | Out-Null
Copy-Item $src ".\.claude\skills\" -Force
New-Item -ItemType Directory -Force ".\.codex\skills" | Out-Null
Copy-Item $src ".\.codex\skills\" -Force
```

On macOS/Linux: `cp .cursor/skills/*.md .agents/skills/` (and same for `.claude/skills`, `.codex/skills`) after `mkdir -p`.
