# Repository Guidelines

## Project Structure & Module Organization
This repository is currently documentation-first. Core project context lives in `docs/superpowers/specs/` and implementation planning lives in `docs/superpowers/plans/`. UI reference images such as `sql-editor-page.png` and `current-page.png` capture expected behavior and layout. OpenSpec configuration is stored in `openspec/config.yaml`.

The design spec in `docs/superpowers/specs/2026-03-18-query-export-design.md` defines the intended app layout:
- `backend/app/` for FastAPI APIs, services, models, schemas, and core config
- `frontend/src/` for Vue views, components, API clients, and stores
- top-level `docker-compose*.yml` and `.env.example` for local orchestration

## Build, Test, and Development Commands
There are no runnable app commands committed yet. Until code lands, use these documentation checks:
- `rg --files docs openspec` to inspect tracked specs and plans
- `sed -n '1,200p' docs/superpowers/specs/2026-03-18-query-export-design.md` to review the canonical architecture
- `git log --oneline` to confirm commit style before contributing

When implementation is added, document the real commands in this file and prefer explicit targets such as `docker compose up`, `npm run dev`, and backend test commands.

## Coding Style & Naming Conventions
Follow the planned stack from the design doc: Python `snake_case` modules for backend code and Vue single-file components in `PascalCase` for frontend UI, for example `QueryEditor.vue`. Use 4 spaces in Python and standard frontend formatter defaults for TypeScript/Vue. Keep file and directory names descriptive and aligned with domain concepts such as `datasources`, `exports`, and `saved_sql`.

## Testing Guidelines
No test framework is configured yet. Once code exists, place backend tests under `backend/tests/` and frontend tests under `frontend/src/__tests__/` or the framework-standard equivalent. Name tests after the behavior under test, such as `test_export_task_retry.py` or `QueryEditor.spec.ts`. Contributors should add tests for new behavior and document any temporary coverage gaps in the pull request.

## Commit & Pull Request Guidelines
Current history uses short conventional-style messages such as `docs: add QueryExport design specification` and `chore: add .worktrees to .gitignore`. Keep that format: `<type>: <summary>`, with common types including `docs`, `chore`, `feat`, and `fix`.

Pull requests should include a clear summary, linked issue or planning doc when applicable, and screenshots for UI-affecting changes. If a change updates architecture or workflow, update the relevant file under `docs/superpowers/` in the same PR.
