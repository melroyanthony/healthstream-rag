# Code Review Instructions

Review every PR across these 8 dimensions with OWASP Top 10 security coverage. Provide findings with severity levels and concrete fixes.

## Review Dimensions

### 1. Correctness
- Logic errors, off-by-one errors, incorrect boundary conditions
- Race conditions and concurrency bugs
- Incorrect error propagation (swallowed exceptions, wrong status codes)
- Missing edge cases (empty input, zero, negative numbers, Unicode)
- Incorrect assumptions about data types or nullability

### 2. Error Handling
- Unhandled exceptions at system boundaries
- Overly broad `except Exception` blocks
- Missing validation before destructuring or indexing
- Inconsistent error response formats across endpoints

### 3. Naming and Readability
- Variables that don't describe what they hold
- Functions named after implementation rather than intent
- Abbreviations that reduce clarity
- Comment rot (comments that contradict the code)

### 4. SOLID Principles
- **SRP**: Classes or functions doing more than one thing
- **OCP**: Hardcoded conditionals that should use extension points
- **LSP**: Subtypes that break parent contracts
- **ISP**: Bloated interfaces forcing empty implementations
- **DIP**: Direct instantiation of concrete dependencies

### 5. DRY Violations
- Duplicate logic across functions or files
- Copy-pasted blocks that differ only in a constant
- Repeated string literals that should be named constants

### 6. Performance
- N+1 query patterns (loops issuing individual DB calls)
- Missing database indexes implied by query patterns
- Unbounded list operations on large datasets (no pagination)
- Unnecessary serialization/deserialization in hot paths
- Synchronous I/O in async contexts

### 7. Security (OWASP Top 10 + HIPAA)

Scan for all 10 OWASP categories plus HIPAA-specific concerns:

| Category | What to Look For |
|----------|-----------------|
| **A01 Broken Access Control** | Missing auth middleware, IDOR (user-supplied IDs without ownership check), patient_id bypass |
| **A02 Cryptographic Failures** | Hardcoded secrets, weak hashing, missing TLS, PHI in logs or API responses |
| **A03 Injection** | SQL via f-strings/concatenation, prompt injection, command injection |
| **A04 Insecure Design** | Missing rate limiting on auth endpoints, cross-patient data leakage |
| **A05 Security Misconfiguration** | Debug mode in production, default credentials, permissive CORS |
| **A06 Vulnerable Components** | Dependencies with known CVEs, `latest` Docker tags |
| **A07 Auth Failures** | JWT without expiry, missing brute-force protection |
| **A08 Integrity Failures** | Unsafe deserialization, missing integrity checks |
| **A09 Logging Failures** | No auth event logging, PHI in log output, no structured logging |
| **A10 SSRF** | User-supplied URLs without allowlist |
| **HIPAA: PHI Leakage** | PHI in error messages, logs, or unredacted vector store metadata |
| **HIPAA: Patient Isolation** | Any code path that could bypass patient_id filtering |
| **HIPAA: Audit Trail** | Missing logging for data access events |

### 8. Test Coverage Gaps
- Public functions with no corresponding test
- Happy path only — no error path or edge case tests
- Missing RAGAS evaluation for RAG pipeline changes
- Missing patient isolation tests for new retrieval code paths

## Severity Levels

| Severity | Criteria | Action Required |
|----------|----------|-----------------|
| **Critical** | Correctness bugs, security vulnerabilities, PHI leakage, patient isolation bypass | Must fix before merge |
| **Warning** | Performance problems, error handling gaps, SOLID violations | Should fix |
| **Suggestion** | Better naming, DRY opportunities, test additions | Would improve quality |
| **Nitpick** | Style-level observations | Optional |

## Review Rules

- Always provide a file path and line reference for every finding
- Never flag style issues as warnings — they are nitpicks at most
- Critical findings require a concrete suggested fix
- Hardcoded secrets and PHI leakage are always CRITICAL
- Distinguish "no vulnerability found" (PASS) from "not applicable" (N/A)
- Only flag issues in lines changed by the PR unless they're security-critical

## Project-Specific: What NOT to Flag

These are intentional patterns in this repository:

- **`patient_id` from JWT, never from request body** — HIPAA isolation by design
- **Separate vector DB classes with factory** — pluggable backends via env var
- **BM25 in-memory in Lambda** — per-patient corpora are small (<10K chunks)
- **No LangChain in query pipeline** — reduces HIPAA audit surface
- **DynamoDB over PostgreSQL** — zero-idle-cost philosophy (ADR-007)
- **`MOCK_AUTH=true` in test env** — test isolation, not a security hole
- **Comprehend Medical mock in local dev** — real API in AWS deployment only
