# Land

Automate PR landing: monitor conflicts, resolve them, wait for CI, squash-merge.

## Workflow

1. **Ensure clean working tree** before pushing
2. **Watch for review comments** - reply with `[codex]` prefix
3. **Address CI failures** if checks fail
4. **Merge only when**: checks pass, feedback acknowledged, up-to-date

## Commands

```bash
gh pr view --json state,mergeable,statusCheckRollup
git fetch origin main
git merge origin/main --no-commit
# Resolve conflicts if any
git add -A && git commit
git push
gh pr checks
gh pr merge --squash --delete-branch
```
