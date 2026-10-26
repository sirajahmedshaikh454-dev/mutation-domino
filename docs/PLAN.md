# Mutation Domino — Implementation Plan

Status legend: `TODO`, `IN_PROGRESS`, `BLOCKED`, `VERIFIED`.
Evidence for every VERIFIED item is recorded in `docs/TEST_EVIDENCE.md`.

## Guardrails

- The product reports **wild-type structural context** only. It never renders or claims a mutant 3D structure.
- pLDDT is predicted local confidence of the wild-type AlphaFold model, never mutation-effect confidence.
- No single in-house "domino score"; no clinical claims; no fabricated data.
- All external data are untrusted and accessed only through bounded adapters.

## Phase 0 — Research and bootstrap

| ID | Task | Owner | Depends on | Acceptance | Status |
|---|---|---|---|---|---|
| P0-1 | Verify UniProt REST and AlphaFold DB endpoints, response fields, terms | Backend | — | `docs/INTEGRATIONS.md` contains verified URLs, samples, license references | IN_PROGRESS |
| P0-2 | Verify Mol* embedding approach and license | Frontend | — | Documented in `docs/INTEGRATIONS.md` | TODO |
| P0-3 | Scaffold backend project, config, lint/test tooling | Backend | — | venv install, `ruff`, `pytest` run | TODO |
| P0-4 | Scaffold frontend (Vite/React/TS/Tailwind) | Frontend | — | `npm run build` works | TODO |
| P0-5 | Docs skeleton + `.env.example` + `.gitignore` + scripts | Lead | — | Files exist | TODO |

## Phase 1 — Offline scientific core

| ID | Task | Owner | Depends on | Acceptance | Status |
|---|---|---|---|---|---|
| P1-1 | Variant parser `A123V` with actionable errors | Bio | — | valid/invalid/wrong-WT/identity/out-of-range tests | TODO |
| P1-2 | Structure parser (PDB + mmCIF) → deterministic residue/atom model, altloc policy | Bio | — | fixture tests incl. altloc, hydrogens, insertion codes | TODO |
| P1-3 | Sequence-to-structure mapping via global alignment + identity/coverage validation | Bio | P1-2 | mapped/gap/insertion code/multichain/mismatch tests | TODO |
| P1-4 | CA neighbors + heavy-atom contacts, NumPy vectorized | Bio | P1-2 | exact distance fixtures, self/hydrogen exclusions, missing CA | TODO |
| P1-5 | Residue chemistry descriptors (versioned static table) | Bio | — | table tests; deltas | TODO |
| P1-6 | Confidence extraction (pLDDT only for AlphaFold; B-factor separate) | Bio | P1-2 | band tests; PDB B-factor never labelled pLDDT | TODO |
| P1-7 | Result/provenance schema + deterministic analysis engine | Bio | P1-1..6 | golden fixture reproducibility test | TODO |

## Phase 2 — Real protein integration

| ID | Task | Owner | Depends on | Acceptance | Status |
|---|---|---|---|---|---|
| P2-1 | Bounded HTTP client (timeouts, size limits, HTTPS allowlist, no user URLs) | Backend | P0 | unit tests for limits/errors | TODO |
| P2-2 | UniProt adapter, accession normalization, caching | Backend | P2-1 | mocked tests with recorded fixture | TODO |
| P2-3 | AlphaFold DB adapter, metadata, structure download, SHA-256 | Backend | P2-1 | mocked tests; malformed/oversized rejected | TODO |
| P2-4 | Disk cache with atomic writes and bounds | Backend | P2-1 | tests | TODO |
| P2-5 | Live smoke test (P69905) recorded with checksum | QA | P2-2/3 | actual retrieved metadata recorded | TODO |

## Phase 3 — API and persistence

| ID | Task | Owner | Depends on | Acceptance | Status |
|---|---|---|---|---|---|
| P3-1 | SQLite/SQLAlchemy tables + Alembic migration + repositories | Backend | P2 | migration on empty DB; CRUD/pagination | TODO |
| P3-2 | REST endpoints + structured error contract | Backend | P1/P2/P3-1 | integration tests, OpenAPI schema tests | TODO |
| P3-3 | JSON export with provenance/version | Backend | P3-2 | parse + schema tests | TODO |
| P3-4 | PDF report with methods/limitations/provenance | Backend | P3-2 | file opens, text extract tests | TODO |
| P3-5 | Fixture mode for offline demo/E2E | Backend | P2 | env flag serves recorded P69905 data | TODO |

## Phase 4 — Frontend and viewer

| ID | Task | Owner | Depends on | Acceptance | Status |
|---|---|---|---|---|---|
| P4-1 | API client, types, error handling, query setup | Frontend | P3 | typecheck + tests | TODO |
| P4-2 | Home / Protein / Analysis / History pages, responsive scientific UI | Frontend | P4-1 | component tests | TODO |
| P4-3 | Mol* wild-type viewer, highlight mutated+neighbors, selection sync, fallback | Frontend | P4-1 | mock Mol* tests; manual/browser check | TODO |
| P4-4 | Exports/history UX, disclaimers, accessibility states | Frontend | P4-2 | tests | TODO |
| P4-5 | Playwright E2E against local backend + fixtures | QA | P4-2..4, P3-5 | analyze → save → reopen → export | TODO |

## Phase 5 — Hardening and release

| ID | Task | Owner | Depends on | Acceptance | Status |
|---|---|---|---|---|---|
| P5-1 | Full quality gate (ruff, mypy, pytest, lint, typecheck, vitest, build) | QA | all | commands pass, recorded | TODO |
| P5-2 | Benchmark representative protein | QA | P2 | timing recorded with machine spec | TODO |
| P5-3 | README Windows + Unix setup, troubleshooting, walkthrough | Lead | all | fresh-clone commands | TODO |
| P5-4 | Scientific limitations + architecture + integrations finalized | Lead | all | docs complete | TODO |
| P5-5 | Security review (SSRF, bounds, XSS, path traversal) | Security | P3 | checklist/evidence | TODO |

## Phase 6 — Optional (not part of MVP)

Functional-site annotations, AlphaMissense, comparison, batch, PDB, sharing — deferred until Phase 5 is green.
