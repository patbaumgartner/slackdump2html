# Contributing

Thanks for considering a contribution.

## Development setup

1. Install uv.
2. Sync dependencies:

```bash
uv sync --all-groups
```

3. Run quality checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run bandit -c pyproject.toml -r src
uv run pip-audit
```

## Pull request process

1. Create a branch from `main`.
2. Add or update tests for behavior changes.
3. Ensure all checks pass locally.
4. Open a pull request with a clear summary, test evidence, and migration notes if needed.

## Commit style

Use concise, imperative commit messages, for example:

- `fix: handle missing slack message blocks`
- `test: add parser edge-case coverage`

## Reporting issues

Please use issue templates and include:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python, project version)
