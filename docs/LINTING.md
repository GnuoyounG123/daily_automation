# Linting plan

This project should use Ruff as the first linting layer. It is fast, works from
`pyproject.toml`, and can cover linting, import sorting, and formatting with one
tool. That is a good fit for a project with many AI-assisted edits because the
feedback loop stays short.

## Current recommendation

Use Ruff in two modes:

```bash
python -m ruff check .
python -m ruff format --check .
```

For local cleanup:

```bash
python -m ruff check . --fix
python -m ruff format .
```

Install development tools with:

```bash
python -m pip install -e ".[dev]"
```

On systems where `python` is not available, use `python3` instead.

## Rule set

The initial configuration enables rules that catch high-signal problems without
forcing a full historical rewrite:

| Rule family | Purpose |
| --- | --- |
| `E4`, `E7`, `E9` | Import placement, syntax-adjacent pycodestyle errors, runtime parse errors |
| `F` | Pyflakes checks such as undefined names and unused imports |
| `I` | Import sorting |
| `B` | Bugbear checks for common Python footguns |
| `C4` | Cleaner comprehensions |
| `SIM` | Simple, lower-risk code simplifications |
| `UP` | Safe Python version upgrades for Python 3.10+ |
| `RUF` | Ruff-specific correctness and cleanup checks |

The project currently ignores `RUF001`, `RUF002`, and `RUF003` because the code
contains Chinese user-facing text where Unicode punctuation and characters are
intentional.

## Adoption path

1. Run Ruff in report-only mode and fix obvious correctness issues.
2. Enable `ruff check . --fix` for import sorting and safe autofixes.
3. Run `ruff format .` in a dedicated formatting commit if the diff is large.
4. Add CI checks:

   ```bash
   python -m compileall -q app.py launcher.py src tests
   python -m ruff check .
   python -m ruff format --check .
   python -m pytest
   ```

5. Add type checking later, starting with modules that already have clear data
   boundaries:
   - `src/daily_automation/config_manager.py`
   - `src/daily_automation/password_crypto.py`
   - `src/daily_automation/app_paths.py`
   - `src/daily_automation/schedule_manager.py`

## What not to do yet

- Do not enable `select = ["ALL"]`; it will create noisy churn before the code
  shape is stable.
- Do not make docstring rules blocking yet. Many current modules have old
  compatibility and script-style docstrings.
- Do not require type checking for the crawling and API modules until external
  response shapes are normalized.
- Do not format generated files, runtime files, package output, or local test
  copies.

## Pull request quality gate

Before merging a code change, run:

```bash
python -m compileall -q app.py launcher.py src tests
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

For UI or task-flow changes, also smoke test:

```bash
python launcher.py web
```
