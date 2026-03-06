# Pull

Synchronize feature branches with origin/main using merge-based updates.

## Steps

1. **Verify clean git status** (commit/stash first)
2. **Enable rerere**: `git config rerere.enabled true`
3. **Fetch latest**: `git fetch origin`
4. **Sync feature branch**: `git pull --ff-only`
5. **Merge origin/main**: `git -c merge.conflictstyle=zdiff3 merge origin/main`
6. **Resolve conflicts** one file at a time
7. **Verify**: `uv run ruff check . && uv run ruff format . --check`
8. **Summarize merge results**

## Conflict Resolution

- Inspect context with `git diff --merge`
- Understand intent on both sides
- Prefer minimal, intention-preserving edits
- Run `git diff --check` to ensure no conflict markers remain
