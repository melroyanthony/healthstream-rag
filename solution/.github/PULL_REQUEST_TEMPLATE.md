## Summary
<!-- 1-3 bullet points describing what this PR does and why -->

- Short summary of the main change

## Related Issues
<!-- Link issues: Closes #N, Refs #M -->

Closes #

## Changes

| File | Change |
|------|--------|
| _path/to/file_ | Short description of change |

## Diagrams
<!-- Optional: Mermaid diagrams for architecture/data flow changes -->

## Test Plan

- [ ] Unit tests pass (`uv run pytest tests/ -v`)
- [ ] Docker Compose builds and starts (`docker compose up --build`)
- [ ] Health check passes (`curl http://localhost:8000/health`)
- [ ] Patient isolation test passes (no cross-patient data leakage)

## Checklist

- [ ] Conventional commit title (`feat:`, `fix:`, `docs:`, `refactor:`)
- [ ] No PHI/secrets in committed code
- [ ] HIPAA controls preserved (patient isolation, PHI redaction)
- [ ] Copilot review comments resolved
