# Repository Guidelines

## Project Structure & Module Organization
- `specs/`: Feature design artifacts (plan, research, data-model, contracts, tasks).
- `.specify/`: Workflow templates and scripts used to generate specs.
- `.github/prompts/`: Prompt files orchestrating the `.specify` workflows.
- `src/`: Python source tree (add packages here, e.g. `src/dvol_data_ingest/`).
- `tests/`: Pytest test suite mirroring `src/` layout.
- Root config: `pyproject.toml` (Poetry), `pytest.ini`, `.env` (local config; not committed).

## Build, Test, and Development Commands
- Install: `poetry install` (Python 3.11 required) and activate via `poetry shell` or prefix with `poetry run`.
- Lint: `poetry run ruff check .` (static checks) and `poetry run black .` (format).
- Tests (unit): `poetry run pytest -q`.
- Tests (integration): `poetry run pytest -m integration -q`.
- CLI (ingest): `poetry run dvol-ingest --help` (entrypoint: `dvol_data_ingest.cli.main:app`).
- Spec workflows (PowerShell): see `.github/prompts/*.md` and `.specify/scripts/powershell/*`.

## Coding Style & Naming Conventions
- Formatting: Black (PEP 8, 4-space indents) + Ruff for linting; fix all Ruff errors.
- Types: Prefer type hints; validate IO with Pydantic models where appropriate.
- Naming: packages/modules `snake_case`; classes `PascalCase`; functions/vars `snake_case`.
- CLI: Typer commands live under `dvol_data_ingest/cli/`; keep command names kebab-case.

## Testing Guidelines
- Framework: Pytest; place tests under `tests/` with files named `test_*.py`.
- Structure: mirror package paths (e.g., `tests/dvol_data_ingest/test_*.py`).
- Markers: use `@pytest.mark.integration` for network/IO paths; default tests remain unit-fast.
- Data contracts: validate schemas in `specs/**/contracts/` using `jsonschema` in tests.

## Commit & Pull Request Guidelines
- Commits: use imperative mood, concise subject (≤72 chars). Example: `Add schema validation for DVOL feed`.
- Prefer focused commits per logical change; include brief body for rationale.
- PRs: include summary, linked issue, scope of changes, test evidence (logs or screenshots), and any schema/contract updates in `specs/`.

## Security & Configuration Tips
- Secrets: store locally in `.env`; do not commit. Load via `python-dotenv`.
- External data sources (e.g., CryptoDataDownload/Deribit): add API keys and endpoints via env vars; mock in tests.

## Agent-Specific Instructions
- Obey this `AGENTS.md` across the repo. When generating artifacts, follow `.github/prompts/*` and `.specify/*` scripts. Use absolute paths when scripts require.
