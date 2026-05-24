# Repository hygiene

This repository previously tracked generated artifacts alongside source files.
The current hygiene policy is:

1. Track source, tests, docs, templates, and small hand-authored scripts.
2. Do not track local secrets, user config, runtime logs, generated reports, or
   PyInstaller output.
3. Keep release binaries outside normal source review unless a release commit is
   intentionally being prepared.

## Private files

These files must stay local:

| Pattern | Reason |
| --- | --- |
| `config.json` | May contain email address, encrypted password, and API keys |
| `.secret_key` | Decrypts Fernet values stored in local config |
| `schedule.json` | User-specific schedule data |
| `weekly_tasks.json` | User-specific planning data |

## Generated files

Generated output belongs in ignored paths:

| Pattern | Reason |
| --- | --- |
| `runtime_local/` | Local config, secrets, generated briefings, and logs |
| `artifacts/` | PyInstaller build output and release packages |
| `release/` | Legacy release residue waiting for manual cleanup |
| `Setup_ForGemini/` | Local distribution scratch directory |

## Historical tracked artifacts

Some generated files are already tracked in Git history. Removing them from the
index should be done as a separate, explicit cleanup commit after reviewing the
current dirty worktree. Candidate paths:

```powershell
git rm --cached -r build2 build_setup data logs release
git rm --cached DailyAutomation.spec Setup.spec build_exe.spec build.bat
git rm --cached check_exe.py debug_config.py pack_release.py run_config_test.py
```

Use `git status --short` after each group. The commands above keep local files
on disk when `--cached` is used, but stage their removal from version control.
