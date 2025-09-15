# Repository Guidelines

## Project Structure & Module Organization
- `specs/`: Spec-first design docs per module (e.g., `001-dvol-forecasting-system/`, `003-data-ingest-module-spec/`) with `spec.md`, `plan.md`, `tasks.md`, and optional `contracts/`.
- `pyproject.toml` and `poetry.lock`: Poetry-managed Python 3.11 project (package-mode disabled).
- `.specify/` templates and scripts; `.claude/` agent settings. Local env in `.venv/`.
- Source code is expected under `src/` (create if missing). Place tests in `tests/`. Keep data local in `data/` (do not commit).

## Build, Test, and Development Commands
- Install toolchain: `poetry install`
- Run tests: `poetry run pytest -q`
- Lint: `poetry run ruff check .`
- Format: `poetry run black .`
- Notebooks: `poetry run jupyter lab`; lint notebooks with `poetry run nbqa ruff notebooks`
- Git hooks: `poetry run pre-commit install` then `poetry run pre-commit run --all-files`

## Coding Style & Naming Conventions
- Python 3.11, 4-space indent, prefer type hints for public APIs.
- Naming: packages/modules `snake_case`, classes `CapWords`, functions/vars `snake_case`, constants `UPPER_SNAKE_CASE`.
- Formatting via Black (default config, ~88 cols). Lint with Ruff; fix issues or add clear justifications.
- Config, secrets, and run-time knobs via `.env` (+ `python-dotenv`). Use UTC for timestamps.

## Testing Guidelines
- Framework: `pytest`. Tests live in `tests/` and follow `test_*.py` naming.
- Markers: `unit` vs `integration` as needed; run fast set with `pytest -q -m 'not integration'`.
- Aim for >80% coverage on new/changed modules. Validate data contracts with `pandera` when applicable.

## Commit & Pull Request Guidelines
- Git history is minimal; adopt Conventional Commits. Examples: `feat(ingest): add DVOL fetch`, `fix(io): handle empty payloads`.
- Branches: `NNN-topic` to align with spec IDs or `feature/<topic>`.
- PRs must include: brief summary, linked spec path (e.g., `specs/003-data-ingest-module-spec/spec.md`), test plan, and evidence (logs/screens) for CLI/ingest changes. All checks (ruff/black/pytest/pre-commit) must pass.

## Security & Configuration Tips
- Never commit secrets or large datasets. `.env` and `.venv/` are already ignored. Prefer `data/` for local outputs and keep it untracked.
- Log in structured form when possible (`LOG_FORMAT=json`); avoid logging credentials.

## Agent-Specific Notes
- Follow spec-first workflow in `specs/`. Keep patches minimal and scoped. Prefer Poetry commands over raw pip. Do not modify unrelated files or add licenses. Document assumptions in PRs.

