# Repository Guidelines

## Project Structure & Module Organization
Library code lives in `src/django_address_kit/` and follows standard Django app layout (`models.py`, `fields.py`, `serializers.py`, `validators.py`). Keep reusable domain logic near `utils.py` or `constants.py`. The `tests/` package mirrors the public API surface with focused test modules, while `examples/` hosts runnable integration snippets and `docs/` contains long-form guidance. Configuration helpers and local settings sit under `config/`, and `manage.py` powers ad-hoc exploration against the bundled `tests.settings` configuration.

## Build, Test, and Development Commands
Use `poetry install` to sync dependencies; avoid mixing pip and Poetry. Run the suite with `poetry run pytest` (defaults to `tests.settings` and enforces coverage). Target a quick check with `poetry run pytest tests/test_models.py::test_valid_address`. Lint before pushing: `poetry run ruff check src tests` for static analysis and `poetry run black src tests` for formatting. Package wheels with `poetry build` once the matrix is green.

## Coding Style & Naming Conventions
Follow Black and Ruff defaults: 4-space indentation, 100-character lines, double quotes for strings unless a literal demands otherwise. Prefer explicit imports and module-level factory functions over singletons. Django models, serializers, and validators should use descriptive PascalCase (`StreetAddressField`), while internal helpers stay snake_case (`normalize_zip`). Keep module names plural only when they expose collections (`formatters.py`).

## Testing Guidelines
Pytest with pytest-django drives validation; each new feature needs unit and integration coverage mirroring modules under test. Name files `test_<feature>.py` and functions `test_<behavior>`. Mark expensive scenarios with `@pytest.mark.performance` so they can be isolated via `poetry run pytest -m performance`. Aim for ≥90% coverage, checking the terminal `--cov-report` output. Add regression fixtures under `tests/fixtures/` if stateful data is required.

## Commit & Pull Request Guidelines
Write imperative, present-tense commit subjects under 72 characters (e.g., `feat: add USPS street formatter`). Group related adjustments into a single commit; avoid drive-by style fixes. Pull requests should describe the motivation, reference issues (`Closes #123`), and include screenshots or sample payloads when behavior changes. Confirm CI, lint, and coverage locally before requesting review, and call out any skipped tests or follow-ups in the PR description.

## Security & Configuration Tips
Protect API keys by using `.env` files ignored by git; inject secrets through Django settings overrides in `tests/settings.py`. Never commit live credentials or customer data. When adding geocoding integrations, keep rate-limiting and logging opt-in so downstream apps control exposure.
