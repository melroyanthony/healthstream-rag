# Stage 4: Bug Fixes

## Bug 1: Guardrails Early Return
- **Symptom**: Denied topic check message was overwritten by grounding check
- **Cause**: `apply_guardrails` checked denied topics, set cleaned message, then grounding check overwrote it
- **Fix**: Return early after denied topic detection (before grounding check runs)

## Bug 2: MRN Regex Pattern
- **Symptom**: "MRN: 12345678" (with colon-space) was not redacted
- **Cause**: `[:\s]?` only matches zero or one character; "MRN: " has colon then space (2 chars)
- **Fix**: Changed to `[:\s]*` to match zero or more colon/space characters

## Bug 3: Test Isolation (ChromaDB persistence)
- **Symptom**: `test_create_collection` returned 409 (duplicate) on fresh test run
- **Cause**: `Settings()` singleton cached `chroma_persist_directory` at import time; changing env var had no effect
- **Fix**: Used FastAPI `dependency_overrides` to inject fresh ChromaDB instances per test
