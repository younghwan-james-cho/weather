# Push

Push current branch changes to origin and manage PRs.

## Prerequisites

- `gh` CLI is installed and `gh auth status` succeeds

## Steps

1. **Identify current branch** and confirm remote state
2. **Run local validation**: `uv run ruff check . && uv run ruff format . --check`
3. **Push branch**: `git push -u origin HEAD`
4. **If rejected**, use pull skill to merge, then retry
5. **Ensure PR exists** - create or update as needed
6. **Write clear PR title** describing the change
7. **Reply with PR URL**

## Commands

```bash
branch=$(git branch --show-current)
uv run ruff check . && uv run ruff format . --check
git push -u origin HEAD
gh pr create --title "Your title here"
gh pr view --json url -q .url
```
