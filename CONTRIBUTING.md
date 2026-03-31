# Contributing to HealthStream RAG

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/melroyanthony/healthstream-rag.git
cd healthstream-rag

# Option A: Docker (recommended)
cd solution && docker compose up --build -d

# Option B: Local dev
cd solution/backend
uv sync
MOCK_AUTH=true uv run uvicorn app.api.main:app --reload --port 8000
```

## Running Tests

```bash
cd solution/backend
MOCK_AUTH=true uv run pytest tests/ -v
```

## Code Standards

- **Python 3.13+** with type hints on all function signatures
- **uv** for package management (never pip directly)
- **Ruff** for linting: `uv run ruff check app/ tests/`
- **Pydantic v2** for validation at API boundaries
- Functions do one thing, max 30 lines (excluding tests)
- Files max 300 lines (split if larger)

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

# Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore
# Examples:
feat(retriever): add cohere rerank backend
fix(guardrails): handle empty context chunks
docs(adr): add ADR-007 for session store choice
```

## Pull Request Process

1. Create a feature branch: `feat/issue-N-description`
2. Make your changes with atomic commits
3. Ensure all tests pass: `MOCK_AUTH=true uv run pytest tests/ -v`
4. Ensure lint passes: `uv run ruff check app/ tests/`
5. Open a PR against `main` with:
   - A clear title following commit convention
   - Description explaining **why**, not just what
   - One label: `feature`, `bug`, `refactor`, `upgrade`, `docs`, `internal`, `breaking`, or `security`
6. Address review feedback

## Architecture

Before making significant changes, please review:

- [System Design](solution/docs/architecture/system-design.md)
- [Architecture Decision Records](solution/docs/decisions/)
- [C4 Diagrams](solution/docs/architecture/c4/)

For new architectural decisions, add an ADR in `solution/docs/decisions/`.

## Reporting Issues

Use [GitHub Issues](https://github.com/melroyanthony/healthstream-rag/issues) with the appropriate template (bug or feature request).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
