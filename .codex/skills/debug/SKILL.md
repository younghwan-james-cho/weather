# Debug

Systematic debugging workflow.

## Steps

1. **Reproduce** the issue consistently
2. **Isolate scope** - which component is affected
3. **Gather info** - errors, recent changes, related files
4. **Form hypothesis** based on evidence
5. **Test hypothesis** with minimal changes
6. **Iterate** until root cause found
7. **Implement fix** with minimal scope
8. **Add regression test** if applicable
9. **Document** in commit message

## Commands

```bash
git log --oneline -10
git diff HEAD~1
grep -r "error" logs/
uv run python -m pdb script.py
```
