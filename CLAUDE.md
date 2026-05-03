# Echofy — agent instructions (Claude Code)

## Session start (required)

1. **Understand the project before editing code.** Read the skill markdown first — at minimum **`overview.md`**, then **`class-project.md`** and **`local-dev.md`** when running or scoping work; add **`html-workflow.md`** for page/HTML changes; open **`api.md`**, **`backend.md`**, **`database.md`**, etc. as needed.
2. **Use the codebase** only when you need detail beyond the docs, or when implementing changes.

### Mirrored roots (same filenames under each `skills/` folder)

| Path | Purpose |
|------|---------|
| `.cursor/skills/` | **Canonical** — edit here first |
| `.agents/skills/` | Mirrored project docs |
| `.claude/skills/` | Claude Code copy |
| `.codex/skills/` | Codex copy |

Also: `README.md`, `.env.example`.

## Database changes and production compatibility (required)

Any change to the **database schema** (new tables, new columns, new indexes or constraints, renamed semantics) **must remain compatible with older databases** that already exist in production or on teammates’ machines after `git pull`.

1. **Never assume a green-field DB only.** After commit and deploy, the live database may still be on an older shape until the app runs its startup path (or until you add an explicit migration). Users must not hit crashes or `OperationalError` / missing-column failures when they use a feature that depends on the new schema.
2. **Ship the upgrade path in code** for this project: extend **`backend/app/schema_sync.py`** (and/or rely on `db.create_all()` for *new* tables) so that at **app startup** the deployed database is brought in line—e.g. missing columns added, legacy duplicates cleaned before unique indexes, new tables created. Register new models in the sync loop where appropriate.
3. **Prefer additive, nullable, or defaulted columns** when possible so old rows remain valid; avoid breaking renames without a transitional step documented in **`.cursor/skills/database.md`**.
4. **Document** the change in **`.cursor/skills/database.md`** (and mirror per below) so agents and humans know what was added and how existing DBs are upgraded.

Details: **`.cursor/skills/database.md`** → *Backward-compatible schema changes*.

## After important changes (required)

For **substantive** work — UI/design, backend or API, database/models, Spotify/integrations, auth/security, deploy/CI, snippet/render workflow — you **must**:

1. **Update** the relevant `*.md` in **`.cursor/skills/`**.
2. **Copy** `.cursor/skills/*.md` to **`.agents/skills/`**, **`.claude/skills/`**, and **`.codex/skills/`** so all copies match.

## Git — commit and push (required)

**Never run `git commit` or `git push` unless the user explicitly asks.** Make code changes, then stop. Wait for the user to say "commit", "commit and push", or equivalent before touching git.

## One-shot sync (bash, repo root)

```bash
mkdir -p .agents/skills .claude/skills .codex/skills
cp .cursor/skills/*.md .agents/skills/
cp .cursor/skills/*.md .claude/skills/
cp .cursor/skills/*.md .codex/skills/
```

On Windows, use the PowerShell block in **`AGENTS.md`**.
