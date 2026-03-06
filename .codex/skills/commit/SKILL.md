# Commit

Create well-formed git commits that reflect actual code changes and session context.

## Steps

1. **Read session history** to identify scope, intent, and rationale
2. **Inspect the working tree** using `git status`, `git diff`, and `git diff --staged`
3. **Stage intended changes** with `git add -A` after confirming scope
4. **Sanity-check** newly added files for random or ignored files
5. **Fix the index** if staging is incomplete or includes unrelated files
6. **Choose a conventional type** (feat, fix, refactor, docs, test, chore)
7. **Write a subject line** in imperative mood, 72 characters or less
8. **Write a body** with summary, rationale, and tests
9. **Append Co-authored-by** trailer: `Co-authored-by: Codex <codex@openai.com>`
10. **Create commit** using `git commit -F <file>`

## Commit Message Template

```
<type>(<scope>): <short summary>

Summary:
- <what changed>

Rationale:
- <why>

Tests:
- <command or "not run (reason)">

Co-authored-by: Codex <codex@openai.com>
```
