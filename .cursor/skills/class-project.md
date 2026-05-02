# Echofy — class project scope

**When to read this:** Planning work for a course submission; deciding how much polish is enough.

## Goals (typical)

- App is **functional**: users can complete the main flows the assignment describes (auth, discover/Spotify touchpoints, reviews, friends, deploy or local demo—whatever the rubric asks for).
- Code is **understandable** and **runs** for the instructor or TA without secret detective work.

## What “good enough” means here

- **Local:** SQLite + `127.0.0.1:5001` API + static frontend on **3001** is fine unless the brief requires cloud.
- **Tests:** No full test suite is assumed. Smoke checks (e.g. `GET /api/health`, manual login + one feature path) are enough unless the course mandates otherwise.
- **UI:** Consistent enough to demo; pixel-perfect design and accessibility audits are optional unless required.
- **Security:** Follow existing patterns (sessions, CORS, no secrets in frontend). Do not skip obvious leaks; do not over-build enterprise controls.

## Prioritize

1. Rubric / assignment checklist (if provided).
2. [`README.md`](../../README.md) and [`.env.example`](../../.env.example).
3. Skill docs in `.cursor/skills/` (then code).

## Avoid for this repo

- Large unrelated refactors, new frameworks, or “while we’re here” rewrites.
- Duplicating documentation in random folders without updating the canonical **`.cursor/skills/`** copies and mirroring per `AGENTS.md`.
