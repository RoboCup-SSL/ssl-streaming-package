# Known bug: uv deletes editable workspace-member source (dir name ≠ package name)

**Status:** worked around (commit `106e9b0`). Logged here so we don't re-trip on it.

## Symptom

On a fresh clone, `./run.sh` worked **once**, then failed on the **second** run with:

```
/…/services/.venv/bin/python: No module named mediamtx_controller
error: invalid [cameras] in field.toml
```

The same happened for `obs_live_data`. The four other workspace members never failed.

## Environment

- **macOS**, zsh.
- **uv 0.11.23** (not reproducible on uv 0.11.3 / Linux).
- uv workspace with **no root `[project]`** (`services/pyproject.toml` is just
  `[tool.uv.workspace]`), members installed as PEP-660 **editable** installs.

## Root cause

The two failing members were exactly the ones whose **directory name differed from the
package name** (hyphen vs underscore):

| directory (old)        | package (import name) |
|------------------------|-----------------------|
| `mediamtx-controller`  | `mediamtx_controller` |
| `obs-live-data`        | `obs_live_data`       |

The four working members all had `dir == package` (`data_access`, `configuration`, …).

For those mismatched members, the **second `uv sync`** *deleted the package source directory
off disk* (e.g. `services/mediamtx-controller/mediamtx_controller/` was removed, leaving only
`README.md` + `pyproject.toml`). The editable `.pth` and `*.dist-info` remained, so the files
looked "installed" but the module was unimportable.

It is **not** a venv prune and **not** missing-from-git — `git ls-files` shows the source is
committed; uv removed it from the working tree on re-sync. This is the nastier form of the
known PEP-660 / editable-install instability on macOS (see references).

### Evidence

- `import mediamtx_controller` → `ModuleNotFoundError`, but `_editable_impl_mediamtx_controller.pth`
  and `mediamtx_controller-0.1.0.dist-info` both present in site-packages.
- The `.pth` contained the correct dir (`…/services/mediamtx-controller`), but that dir's
  `mediamtx_controller/` subdir was gone (`ls` → "No such file or directory").
- `git ls-files` confirms the source is committed.
- 100% correlation: only the two `dir != package` members failed.

## Fix

1. **Rename the member directories to match their packages** so every member is `dir == package`
   (like the four that always worked):
   - `services/mediamtx-controller/` → `services/mediamtx_controller/`
   - `services/obs-live-data/` → `services/obs_live_data/`

   (`[project]` names stay hyphenated — the working members use hyphenated names too, so the
   distribution name is *not* the trigger; the directory name is.)
2. Update the workspace `members` list, regenerate `uv.lock`, and fix dir-path references
   (`scenes.json` logo paths, the logos test, docs).
3. **Defense in depth:** `run.sh` no longer runs `uv sync` on every launch (the *re-sync* was
   the trigger). `setup.sh` builds the venv **fresh** once (`rm -rf .venv && uv sync --all-packages`);
   `run.sh` just uses `services/.venv/bin/python` and a check that the members import.

## Why it works

A single fresh sync never triggered the deletion (run 1 always worked); only the second sync
did. Making `dir == package` removes the mismatch that uv mishandles, and never re-syncing over
an existing venv removes the trigger entirely. Both together: belt and suspenders.

## Rule going forward

**Every workspace member's directory name must equal its package (import) name.** Don't add a
member dir like `foo-bar/` containing package `foo_bar/`.

## References

- uv #15448 — editable install src missing from sys.path: https://github.com/astral-sh/uv/issues/15448
- uv #3898 — PEP-660 editable breakage: https://github.com/astral-sh/uv/issues/3898
- FHS `/var/tmp` (unrelated, used elsewhere): https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s15.html
