# Test evidence

Date: 2026-10-25
Environment: Windows, Python 3.13, Node LTS

Commands:
- `cd backend && python -m pytest` -> 96 passed, 1 warning.
- `cd backend && ruff check . && ruff format --check .` -> All checks passed.
- `cd backend && python -m mypy app` -> Success: no issues found.
- `cd frontend && npm run lint` -> 0 errors, 0 warnings.
- `cd frontend && npm run typecheck` -> success.
- `cd frontend && npm run test -- --run` -> 1 file, 2 tests passed.
- `cd frontend && npm run build` -> success.