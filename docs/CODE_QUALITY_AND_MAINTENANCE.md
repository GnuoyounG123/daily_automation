# Code quality and maintenance pipeline

This project is heavily based on vibe coding, so quality assurance must be
explicit, repeatable, and cheap to run. The goal is not to slow iteration down;
the goal is to keep fast changes from becoming invisible risk.

## Quality principles

| Principle | Rule |
| --- | --- |
| Small changes | Prefer narrow commits that touch one behavior, one UI area, or one module boundary. |
| Traceable intent | Every non-trivial change should name the user problem, expected behavior, and files touched. |
| Tests before trust | Passing manual checks are useful, but automated tests are the baseline for accepting changes. |
| Runtime state isolation | Local secrets, logs, generated reports, and package output stay outside source review. |
| Compatibility preserved | Root-level compatibility wrappers must keep old commands working unless a migration is planned. |
| Docs follow behavior | Entry point, config, packaging, or workflow changes must update `README.md` or `docs/`. |

## Branch and change workflow

1. Start from `main` and pull the latest upstream state.
2. Create a short-lived branch for each change, using a clear name such as
   `feature/web-config-validation` or `fix/email-error-summary`.
3. Before editing, identify the owned area:
   - web UI: `src/daily_automation/web_app.py`
   - backend workflow: `src/daily_automation/daily_assistant.py`
   - configuration: `src/daily_automation/config_manager.py`
   - scheduling: `src/daily_automation/schedule_manager.py`
   - fetch/parse/API behavior: `web_fetcher.py`, `html_parser.py`, `api_sources.py`
4. Keep root Python files as compatibility wrappers. New logic belongs in
   `src/daily_automation/`.
5. Add or update tests for changed behavior.
6. Run the local quality gate before merging.
7. Merge only after review, a clean status, and documented follow-up items.

## Local quality gate

Run these checks before a change is considered ready:

```bash
python -m compileall -q app.py launcher.py src tests
python -m pytest
```

For UI or workflow changes, also run the app manually:

```bash
python launcher.py web
```

Manual smoke checklist:

- The web UI starts at `http://localhost:8501`.
- The configuration page loads without crashing.
- Missing API keys or email settings produce visible warnings instead of tracebacks.
- "Generate today briefing" shows progress and either output or a clear error summary.
- Generated files land under `runtime_local/data/`, not the repository root.

## Recommended automated checks

Add these tools incrementally. Do not block feature work on adopting all of
them at once.

| Layer | Tool | Purpose | Suggested command |
| --- | --- | --- | --- |
| Syntax | `compileall` | Catch import and syntax errors | `python -m compileall -q app.py launcher.py src tests` |
| Unit tests | `pytest` | Verify core behavior | `python -m pytest` |
| Formatting | `ruff format` | Keep style consistent | `python -m ruff format .` |
| Linting | `ruff check` | Catch common bugs and unused code | `python -m ruff check .` |
| Types | `mypy` or `pyright` | Protect module boundaries | Start with `config_manager`, `schedule_manager`, and `password_crypto` |
| Security | `pip-audit` | Flag vulnerable dependencies | `python -m pip_audit` |

See `docs/LINTING.md` for the concrete Ruff configuration and rollout plan.

Adoption order:

1. Add Ruff formatting and linting.
2. Add a CI workflow for compile and pytest.
3. Add dependency audit as a non-blocking scheduled check.
4. Add type checking module by module after core APIs stabilize.

## Test strategy

| Area | Minimum coverage |
| --- | --- |
| Config | Defaults, missing files, invalid JSON, secret-safe serialization |
| Password crypto | Round trip, wrong key behavior, missing key creation |
| Schedule | Empty schedule, recurring weekly tasks, malformed task input |
| Fetching | Timeout, HTTP error, invalid HTML/RSS, fallback parser path |
| Academic APIs | API disabled, missing key, empty results, malformed remote response |
| Email | Missing credentials, SMTP failure, dry-run output |
| Web UI | Page import smoke tests and backend function tests; avoid brittle pixel assertions |

Testing rules:

- Use temporary directories for runtime data in tests.
- Never require real API keys, email accounts, or network access in unit tests.
- Mock external HTTP and SMTP boundaries.
- Add regression tests for every bug that reaches manual testing or a user run.

## Review checklist

Use this checklist for every meaningful change:

- Does the change belong in `src/daily_automation/` instead of a root wrapper?
- Are local-only files still ignored?
- Are user-facing errors clear and actionable?
- Can the feature fail safely when the network, API key, or email server is unavailable?
- Does the change preserve existing CLI commands?
- Are tests added or updated near the changed behavior?
- Were docs updated if entry points, config, or workflow changed?
- Is the diff free of generated files, logs, secrets, archives, and build output?

## Release pipeline

1. Confirm the working tree contains only intentional changes.
2. Run the local quality gate.
3. Run the web UI smoke checklist.
4. Update `README.md`, `projects.md`, or `docs/` when behavior changed.
5. Create a release branch or tag only after tests pass.
6. For packaged desktop builds, build from a clean tree:

   ```bash
   python -m PyInstaller packaging/pyinstaller/build_exe.spec --clean --noconfirm
   ```

7. Put binaries and archives under ignored output directories such as `artifacts/`
   or `dist/`.
8. Record release notes with:
   - user-visible changes
   - fixed bugs
   - known limitations
   - manual checks performed

## Maintenance cadence

| Cadence | Work |
| --- | --- |
| Every change | Compile, tests, review checklist, no generated files |
| Weekly | Run app smoke test, inspect logs for repeated failures, prune stale TODOs |
| Monthly | Update dependencies in a branch, run tests, review API source failures |
| Before release | Full quality gate, web smoke test, packaging test, release notes |
| After incident | Add regression test, document root cause, update checklist if needed |

## Vibe coding guardrails

Fast AI-assisted changes are welcome, but each generated change must pass
through these guardrails:

- Ask what invariant the change must preserve before editing shared modules.
- Prefer replacing duplicated generated logic with one small local helper.
- Delete dead generated code in the same change that makes it obsolete.
- Treat network, file system, email, and API boundaries as failure-prone.
- Keep prompts, experiments, scratch files, and generated artifacts out of Git.
- Convert successful manual fixes into tests before moving on.

## Definition of done

A change is done when:

- The intended behavior is implemented.
- Tests or a documented manual check cover the changed path.
- The local quality gate passes.
- No secrets, logs, generated reports, or build artifacts are staged.
- Relevant docs are updated.
- Known follow-up work is recorded instead of hidden in memory.
