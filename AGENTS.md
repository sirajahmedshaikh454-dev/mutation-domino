# AGENTS.md — Mutation Domino

> Master engineering contract for autonomous coding agents building **Mutation Domino**, a confidence-aware protein missense-variant structural-context explorer.
>
> **Status:** Implementation specification, not a claim that the software already works. Agents must execute tests and record evidence before declaring completion.

## 0. Mission and non-negotiable scientific boundary

Build a complete, locally runnable, zero-paid-service web application that accepts a UniProt accession, retrieves an experimentally determined structure where appropriate or an AlphaFold Protein Structure Database prediction, allows a user to specify a single amino-acid substitution, and produces a reproducible **structural-context report**: residue neighborhood, contacts, confidence, physicochemical property changes, annotated functional features, and evidence-linked cautions. Provide an interactive 3D structure viewer, shareable analyses, and downloadable JSON/PDF reports.

**Never claim that the wild-type AlphaFold structure shows the mutant's actual 3D conformation.** Contact changes, stability changes, pathogenicity, binding disruption, or functional consequences cannot be inferred as measured outcomes from a single wild-type model. Label outputs as *context*, *heuristics*, or *hypotheses*. Do not present a homegrown score as a validated pathogenicity predictor. Do not equate pLDDT with mutation-effect confidence. The tool is for research/education, **not clinical decision-making**.

No paid API keys, GPUs, model training, external LLM, or AlphaFold inference are required for the MVP. The AlphaFold database hosts existing predictions; AlphaMissense is a separate optional source of precomputed missense-effect scores and is not AlphaFold's structural-change prediction. Optional enrichment must never block core analysis.

## 1. Working rules for every coding agent

1. Inspect the repository and this document before changing files. Do not assume scaffolding exists.
2. Maintain `docs/PLAN.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`, and `docs/TEST_EVIDENCE.md`. Mark tasks `TODO`, `IN_PROGRESS`, `BLOCKED`, or `VERIFIED` with commands and outputs.
3. Work in small vertical slices. After each slice run formatter, static checks, relevant tests, and at least one functional smoke test. Fix failures before proceeding.
4. Never fabricate executed test results, screenshots, metrics, scientific citations, API responses, or feature completion.
5. External API shapes, URLs, rate limits, licenses, and availability must be verified against current official documentation and saved as links in `docs/INTEGRATIONS.md`; isolate them behind adapters. Do not assume AlphaFold has every UniProt accession.
6. All external data are untrusted. Validate input, timeouts, redirects, response size, content type, file contents, and accessions. Never allow arbitrary server-side URL fetching.
7. Keep deterministic analysis separate from API adapters, UI, and persistence. Make the calculation library independently testable with fixtures and no network.
8. No secrets in source control, logs, exports, or screenshots. `.env.example` must use placeholders only.
9. If an integration is unavailable, show a meaningful failure or explicitly labeled partial result; never silently substitute fake biology.
10. Ask the human only for truly blocking choices or credentials. Otherwise follow defaults in this file and continue.
11. Preserve accessible UX, meaningful loading/empty/error states, and responsive layouts.
12. Do not merge changes that fail the acceptance criteria. When blocked, report the exact cause, reproduction, and next action.

## 2. Product scope

### MVP (mandatory)
- UniProt accession entry and validation; protein metadata (name, organism, sequence, length) from UniProt REST.
- Structure discovery/download via an official AlphaFold DB endpoint; retain source URL, version/model metadata where available, retrieval timestamp, SHA-256 checksum, and sequence/structure mapping.
- Accept a missense substitution in canonical syntax `A123V` (one-letter WT, 1-based canonical position, mutant); show precise errors for invalid syntax, out-of-range, wild-type mismatch, identity substitution, unmapped residues, and unavailable structures.
- Handle sequence numbering correctly: canonical UniProt positions vs PDB/mmCIF auth/label numbering, insertion codes, missing residues, chains, and isoforms. **Fail closed** on ambiguous mappings; never assume sequence index equals PDB residue number.
- Compute wild-type structural context: CA distance neighbors (default 8 Å), heavy-atom proximity (default 5 Å), residue contacts (configurable), residue exposure proxy only if supported by an implemented and tested algorithm, pLDDT if present, and wild-type/mutant residue properties.
- Distinguish pLDDT (predicted-model local confidence) from experimental B factors; if confidence not available, show `not available`.
- 3D viewer: wild-type structure, mutated position highlight, neighbor highlights, color by confidence when meaningful, legend, residue details, selection sync, reset, and fallback if WebGL unavailable.
- Clearly marked interpretation: structural neighborhood, property changes, potential questions to investigate; **not** observed mutant effects.
- Persist analyses in local SQLite; list/reopen analyses; JSON export and PDF report; all results include provenance and method parameters.
- Unit, integration (mocked external services), and end-to-end tests; reproducible local setup.

### V1 enhancements (after MVP passes)
- UniProt feature annotations and known functional-site overlap with explicit source/version and coordinates.
- Optional AlphaMissense precomputed variant lookup where a legitimate, maintained downloadable/accessible data source is verified; show original score semantics, provenance, and coverage gaps, without conflating score with structural evidence.
- Compare two mutations on the same protein (same structure and settings).
- CSV batch analysis with bounded workload and export.
- Optional experimentally determined PDB structures, only with robust chain-to-UniProt mapping and explicit structure-type labeling.
- Optional report links/guest sharing with expiration, authentication, and rate limiting; not part of MVP.

### Out of scope / prohibited shortcuts
- De novo mutant structure prediction or AlphaFold retraining.
- Unsupported delta-delta-G, pathogenicity classification, docking, clinical risk prediction, or 'domino propagation' as experimentally established biology.
- Scraping sites when a documented API/download exists.
- Requiring Redis, Celery, Kubernetes, cloud accounts, or external LLMs for local MVP.

## 3. Reference architecture

```text
Browser (React + TypeScript + Vite)
  ├── Search / Protein overview / Variant editor
  ├── Mol* 3D structure viewer
  ├── Analysis panels / provenance / export / history
  └── Typed API client
              │ HTTP JSON, same-origin proxy in dev
              ▼
FastAPI (Python 3.11+)
  ├── API routes + Pydantic contracts + error mapping
  ├── Application services / orchestration
  │     ├── UniProt adapter (metadata, canonical sequence)
  │     ├── AlphaFold DB adapter (model metadata + structure)
  │     ├── Mapping validator (canonical ↔ structure residue)
  │     ├── Structural analysis engine (pure Python)
  │     └── Report/export service
  ├── SQLAlchemy + Alembic → SQLite
  └── Bounded disk cache (validated structures and metadata)

External sources: UniProt REST; AlphaFold DB official endpoints
Optional later: AlphaMissense precomputed data; PDB/RCSB
```

**Execution flow:** user enters accession → API validates → fetches metadata and structure (cached) → validates sequence-to-structure mapping → user enters variant → analysis service runs deterministic calculations → database saves structured result → browser renders Mol* structure and explanatory panels → export endpoint returns report.

### Design principles
- Backend owns scientific calculations and mapping. Frontend never invents computed biological claims.
- Every analysis stores a schema version, algorithm version, parameters, data-source versions/URLs, retrieval timestamps, checksums, mapping method, and warnings.
- Use a synchronous request for small structures initially with a strict processing timeout and clear 413/422/503 errors; migrate heavy tasks to background jobs only if benchmark evidence requires it.
- Offline deterministic tests must pass without Internet. Online smoke tests are separate and explicitly labeled.

## 4. Technology choices (fixed defaults)

| Layer | Default | Reason / constraint |
|---|---|---|
| Frontend | React, TypeScript, Vite | Fast, maintainable SPA |
| UI | Tailwind CSS, shadcn/ui or Radix primitives, Lucide | Accessible components |
| Data | TanStack Query | Server-state caching, retries configured conservatively |
| 3D | Mol* (`molstar`) | Protein structure visualization; verify API integration |
| Backend | Python 3.11+, FastAPI, Uvicorn | Typed HTTP API |
| Validation | Pydantic v2 | Explicit request/response schemas |
| HTTP | httpx | Timeouts, retries, redirect control |
| Structures | Biopython (`Bio.PDB`) + NumPy | mmCIF/PDB parsing, distances |
| Optional exposure | FreeSASA or Biopython Shrake–Rupley | Use only after tested on fixtures |
| DB | SQLite + SQLAlchemy 2 + Alembic | Zero-cost local persistence |
| PDF | ReportLab | Server-side reproducible report |
| Tests | pytest, pytest-asyncio, respx, Vitest, Testing Library, Playwright | Layered verification |
| Lint/types | Ruff, mypy or pyright, ESLint, TypeScript strict | Quality gates |
| Dev | npm, Python venv, Makefile or cross-platform scripts | No Docker dependency |
| Optional deployment | Docker Compose single-host | Explicitly optional |

Pin compatible versions in lockfiles after installing and testing. Avoid hardcoding guessed version numbers in this spec. Node LTS and supported Python must be verified at implementation time. A single command must start each service; provide Windows PowerShell and Unix instructions.

## 5. Repository layout

```text
mutation-domino/
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docs/
│   ├── PLAN.md
│   ├── DECISIONS.md
│   ├── PROGRESS.md
│   ├── TEST_EVIDENCE.md
│   ├── INTEGRATIONS.md
│   ├── SCIENTIFIC_LIMITATIONS.md
│   └── ARCHITECTURE.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/{routes,schemas,errors}.py  # adapt layout as needed
│   │   ├── core/{config,logging,security}.py
│   │   ├── integrations/{uniprot,alphafold}.py
│   │   ├── domain/{models,mapping,properties,contacts,confidence}.py
│   │   ├── services/{proteins,analysis,reports}.py
│   │   ├── persistence/{database,tables,repositories}.py
│   │   └── exports/{json_export,pdf_export}.py
│   └── tests/{unit,integration,fixtures}/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── index.html
│   ├── src/
│   │   ├── app/
│   │   ├── pages/{Home,Protein,Analysis,History}.tsx
│   │   ├── components/{ProteinViewer,VariantEditor,ContactTable,ConfidenceLegend}.tsx
│   │   ├── features/{proteins,variants,analyses}/
│   │   ├── lib/{api,types,validation}.ts
│   │   └── styles/
│   └── tests/
├── e2e/
└── scripts/{dev,smoke,seed_fixtures}/
```

The illustrative `{...}` notation describes file groups, not literal required filenames. Keep imports coherent and do not create empty placeholder modules just to match a diagram.

## 6. External integrations: contract and safety

### UniProt
Use the documented UniProt REST API to retrieve the **canonical accession**, primary amino-acid sequence, length, protein name, organism, and feature annotations when needed. Normalize accessions and make the sequence used in validation visible. Treat isoforms as unsupported unless explicitly mapped. Follow official usage guidance, include an identifying User-Agent when appropriate, and cache responses.

### AlphaFold DB
Use official AlphaFold DB documented endpoints for structure metadata and downloadable mmCIF/PDB. Prefer mmCIF when practical. Do not assume the endpoint path, file naming convention, coverage, or data license without verification. Reject malformed or oversized downloads; store checksums. Handle missing predictions and model versions explicitly. Predicted-model pLDDT may be stored in B-factor-like fields; identify model provenance before interpreting it. Distinguish missing coordinates from missing sequence residues.

### Optional AlphaMissense
Never make it a hard dependency. Verify official access terms, downloadable format, UniProt/sequence mapping, model coverage, and score semantics. Display source scores as **external model estimates**, not ground truth or a structural effect inferred by Mutation Domino.

### Error contract
Return structured JSON `{ "error": { "code": "...", "message": "...", "details": {} } }` with appropriate HTTP status. Examples: `INVALID_ACCESSION`, `PROTEIN_NOT_FOUND`, `STRUCTURE_UNAVAILABLE`, `VARIANT_WT_MISMATCH`, `POSITION_UNMAPPED`, `AMBIGUOUS_MAPPING`, `UPSTREAM_TIMEOUT`, `STRUCTURE_TOO_LARGE`, `ANALYSIS_FAILED`. Do not leak tracebacks to clients.

## 7. Scientific computation specification

### 7.1 Variant validation
- Regex: `^([ACDEFGHIKLMNPQRSTVWY])(\d+)([ACDEFGHIKLMNPQRSTVWY])$` after trim/uppercase.
- Position is positive and 1-based; compare WT letter to canonical UniProt sequence at `position - 1`.
- Reject WT == mutant. For ambiguous residues or noncanonical amino acids, reject with an actionable message in MVP.
- Confirm canonical residue maps unambiguously to a resolved residue in the chosen structure chain.

### 7.2 Mapping
Create an explicit mapping object `{canonical_position, structure_chain, structure_residue_id, residue_name, mapping_status}`. Use documented sequence alignment or trusted residue mapping with validation. Verify residue identity and coverage. Report alignment gaps and mismatches. Never infer by simply adding an offset. Structure numbering and alternate locations must be handled deterministically. Tests must include missing N-terminal residues, insertion codes, multiple chains, and a mismatch.

### 7.3 Neighborhood and contacts
- Use the wild-type structure, a specified chain, and standard residues with resolved atoms.
- CA neighbors: Euclidean distance from mutated-position CA to other residue CAs, `<= 8.0 Å` default, exclude self. Clearly mark when CA is absent.
- Heavy-atom contacts: minimum Euclidean distance between **non-hydrogen atoms** in distinct residues, `<= 5.0 Å` default. Exclude self, handle alternate conformers deterministically, and avoid counting missing atoms.
- Distinguish CA neighbors from heavy-atom contacts in labels and exports. Do not call contacts hydrogen bonds, salt bridges, or energetic coupling unless validated methods are implemented.
- Performance: NumPy vectorization and optional spatial indexing; set resource limits; benchmark a realistic protein.
- Optional solvent accessibility: use a tested algorithm and explicitly state relative vs absolute SASA, reference maxima, probe radius, and structure-only limitations. Omit rather than guess if unavailable.

### 7.4 Residue chemistry
Provide a transparent, versioned static table for residue classes (charged, polar, nonpolar, aromatic, etc.) and property deltas (charge category, side-chain size proxy, hydropathy if sourced). Label these as coarse descriptors, not energy or function predictions. Document sources and exact scale.

### 7.5 Confidence and interpretation
For predicted structures, show per-residue pLDDT and familiar confidence bands only after checking official definitions; explain that pLDDT is confidence in the **wild-type predicted local structure**, not mutation outcome. For experimental structures, do not treat B factors as pLDDT. For absent confidence data, display `N/A`.

**MVP report text pattern:**
- Observation: “In the supplied wild-type model, residue X has N CA neighbors within 8 Å.”
- Descriptor: “The substitution changes the residue category from A to B.”
- Caution: “This does not establish a changed contact network or functional impact after mutation.”
- Provenance: structure, sequence, mapping, thresholds, dates, version, warnings.

**Do not implement a single unvalidated 'domino score' in MVP.** If desired later, introduce a named exploratory ranking metric, mathematically specify it, test sensitivity, benchmark against baselines, and explicitly label it non-clinical.

## 8. Data contracts and persistence

### REST endpoints (versioned `/api/v1`)
- `GET /health` → status/version (no external dependency required).
- `GET /proteins/{accession}` → normalized metadata, canonical sequence, source provenance, structure availability.
- `GET /proteins/{accession}/structure` → safe same-origin structure stream or cached artifact; never an arbitrary URL proxy.
- `POST /analyses` → body `{ "accession":"P69905", "variant":"A10V", "parameters": {"ca_radius_angstrom":8.0,"heavy_atom_radius_angstrom":5.0} }`; response includes analysis ID, status, normalized variant, structural context, warnings, and provenance. **Example only; it is not a claim that this example variant maps successfully.**
- `GET /analyses/{id}` → saved analysis.
- `GET /analyses?limit=20&offset=0` → paginated history.
- `GET /analyses/{id}/export.json` → versioned JSON download.
- `GET /analyses/{id}/report.pdf` → generated PDF with method, interpretation and limitations.

Generate OpenAPI from FastAPI and typed TS contracts from its schema where practical. All response structures need examples and schema tests.

### Database schema (minimum)
- `proteins`: accession, canonical_sequence, metadata_json, retrieved_at, source_version.
- `structures`: id, accession FK, source, model_version, chain, file_path, checksum, mapping_json, retrieved_at.
- `analyses`: UUID, accession FK, structure FK, variant, parameters_json, result_json, algorithm_version, warnings_json, created_at.

Use schema migrations; index accession and created_at; never trust DB JSON to substitute for validation. Implement cache invalidation/versioning, disk bounds, and no raw sequence/structure downloads in the DB unless intentionally designed.

## 9. UI/UX specification

Design a credible scientific SaaS-style interface, not a generic form demo:
1. **Home:** concise mission, UniProt search, example accession, clear non-clinical disclaimer.
2. **Protein overview:** protein name, organism, length, canonical sequence, structure availability, confidence summary where available, sequence-position navigation.
3. **Analysis workspace:** left variant input/settings; center Mol* structure; right observations, contact table, confidence, residue chemistry, warnings. Clicking a table residue focuses/highlights it in Mol*; viewer selection updates detail panel.
4. **History:** persisted analyses with date, accession, variant, reopen, JSON/PDF actions.
5. **Error/empty states:** unknown accession, no model, unmapped position, network unavailable, WebGL unsupported.

Use accessible form labels, keyboard operation, tooltips explaining Å/pLDDT, loading indicators, responsive stacking, and meaningful contrast. Do not render a fabricated mutated model; label the 3D view **Wild-type reference structure**. For PDF, include data provenance, date, calculations, limitations, and a simple static snapshot only if technically reliable.

## 10. Security, resilience, privacy

- Strict accession/variant/parameter allowlists; bounded radii, max sequence/structure size, max result rows, pagination limits.
- httpx with explicit connect/read timeouts, limited retries with jitter for transient errors, bounded redirects (prefer none), allowed HTTPS upstream hostnames, and response byte limits. Prevent SSRF by prohibiting user-supplied URLs.
- No raw uploaded files in MVP; if introduced later, sandbox parsing and restrict file size/type.
- Escape untrusted metadata in HTML/PDF; avoid unsafe Markdown/HTML rendering.
- CORS restricted to configured local frontend origin; no wildcard credentials.
- Use UUID identifiers, safe path joins, atomic cache writes, and avoid concurrent cache corruption.
- Local unauthenticated history is shared among local users of the same deployment; warn clearly. **Do not expose publicly without authentication and isolation.**
- No secrets in logs. Rate limiting and authentication are required before public multi-user deployment.
- Track external source attribution/license obligations before redistribution.

## 11. Agent roles and coordination

If multi-agent orchestration is available, assign roles; otherwise one agent executes them sequentially:

- **Orchestrator / Tech Lead:** owns plan, scope, dependency graph, API contracts, final integration, and release checklist.
- **Bioinformatics Agent:** validates mapping, residue chemistry, contacts, confidence, and scientific disclaimers; writes numerical fixtures.
- **Backend Agent:** API, adapters, caching, persistence, migrations, exports, errors.
- **Frontend Agent:** responsive pages, Mol* viewer, selection synchronization, forms, state, accessibility.
- **QA Agent:** fixtures, tests, browser flows, performance, cross-platform install, regression checks.
- **Security/DevOps Agent:** threat model, input/network bounds, Docker optional, reproducibility, CI, documentation.

**Coordination contract:** agents communicate through `docs/PLAN.md`, API/OpenAPI schemas, test fixtures, and reviewed pull requests or clearly separated branches. Do not concurrently edit the same file without ownership. Each agent's handoff includes changed files, commands executed, observed results, risks, and remaining work. Orchestrator resolves schema conflicts before UI/API implementation diverges.

## 12. Mandatory build order and gates

### Phase 0 — Research and repository bootstrap
- Verify official UniProt, AlphaFold DB, Mol*, and optional AlphaMissense docs/terms.
- Record exact endpoints and sample response fields in `docs/INTEGRATIONS.md`.
- Initialize repo, Python project, frontend, `.gitignore`, `.env.example`, scripts, docs, and CI.
- Gate: clean install and backend/frontend hello-world; formatter/type checks pass.

### Phase 1 — Offline scientific core
- Build fixtures (small known PDB/mmCIF and canonical sequence with verified residue map).
- Implement variant parsing, alignment/mapping validation, CA/heavy-atom distances, chemistry descriptors, confidence extraction, provenance schema.
- Gate: all deterministic unit tests pass offline, including invalid/missing/mismapped cases.

### Phase 2 — Real protein integration
- Implement official UniProt and AlphaFold adapters, timeout/error handling, bounded caching, structure validation.
- Gate: mocked adapter tests pass; optional real online smoke test records actual accession, retrieved model and checksum; no assumption that the online service is always available.

### Phase 3 — API and persistence
- Implement REST endpoints, SQLAlchemy/Alembic, report JSON/PDF, error contracts.
- Gate: integration tests create/reopen/export an analysis using fixtures; migration works on empty DB; API docs available.

### Phase 4 — Frontend and viewer
- Build full workflow and Mol* wild-type viewer, position highlighting, contact selection sync, history, download actions.
- Gate: component tests pass; Playwright runs end-to-end against local services and fixture-backed responses; accessibility smoke test.

### Phase 5 — Hardening and release
- Run all tests, build production frontend, lint/type-check, review warnings and documentation, benchmark one representative protein, verify Windows + Unix instructions where available.
- Gate: README's fresh-clone setup works in a clean environment; no critical security issues; all core acceptance tests green.

### Phase 6 — Optional enhancements
Only after Phase 5: functional-site annotations, AlphaMissense, batch mode, comparisons, public deployment/auth. Each is feature-flagged, tested, and separately documented.

## 13. Testing matrix (required)

**Scientific unit tests:** parser accepts valid substitution and rejects malformed/wrong-WT/identity/out-of-range; known Euclidean CA distances; heavy-atom min distances; excludes self/hydrogen; handles missing CA and alternate conformations; mapping gaps/insertion codes/multiple chains; experimental B factors not shown as pLDDT; identical input yields deterministic output.

**API integration tests:** successful protein lookup and analysis; upstream 404/429/500/timeout; malformed JSON and corrupt mmCIF; invalid parameter bounds; large response rejected; database persistence/migration; exports parse and PDF opens; provenance preserved.

**Frontend tests:** search and form validation; loading/error/empty states; viewer fallback; variant highlights; neighbor table interaction; history reload; exports; keyboard accessibility.

**End-to-end:** start both services from documented commands; use a stable fixture/mocked upstream; analyze one valid substitution; inspect 3D reference viewer; save/reopen; download and validate JSON/PDF. Real-service smoke test is additional and may be skipped offline with explicit notice.

**Quality commands (adapt to actual project):**
```bash
cd backend && python -m pytest -q
cd backend && ruff check . && ruff format --check .
cd frontend && npm ci && npm run lint && npm run typecheck && npm run test -- --run && npm run build
# Playwright: use the repository's documented start/test script
```

Do not mark a test verified if the command was not run. If runtime limitations prevent testing, label it `NOT_RUN` and describe exactly how the user can run it.

## 14. Performance and deployment

MVP targets (not guarantees): ordinary single-chain proteins should analyze in seconds after cache warmup; report actual benchmarks and machine specs. Optimize only after profiling. Bound concurrent downloads, parse time, structure size, and cache usage. Lazy-load Mol* to reduce initial bundle. Avoid O(N²) full-protein pair matrices where spatial indexing suffices.

Local run: Python virtual environment + npm install; SQLite and cache created automatically in configured data directory. Provide `.env.example` for upstream base URLs, `DATABASE_URL`, `CACHE_DIR`, `MAX_STRUCTURE_BYTES`, `FRONTEND_ORIGIN`, and timeouts. No Docker, account, key, or GPU required. Optional Docker Compose is allowed for convenience, but must not become the only working route.

Before internet-facing deployment add: authentication, per-user data ownership, authorization tests, rate limits, HTTPS, structured monitoring, backup/retention policy, abuse protection, and source-license review. SQLite is acceptable for single-instance local MVP, not an unexamined global SaaS default.

## 15. README and deliverables

Required repository outputs:
- Complete source code, pinned lockfiles, sample `.env.example`, migrations, fixtures, and tests.
- `README.md`: prerequisites, exact Windows PowerShell and Unix commands, troubleshooting, example walkthrough, screenshots from a **real running build**, test commands, limitations, and citations/attributions.
- `docs/ARCHITECTURE.md`: components, data flow, failure paths, storage model, API schema.
- `docs/SCIENTIFIC_LIMITATIONS.md`: what is measured, what is inferred, what cannot be concluded, pLDDT semantics, mapping caveats, AlphaMissense separation.
- `docs/INTEGRATIONS.md`: verified current endpoints, terms, versioning, fallback behaviors.
- `docs/TEST_EVIDENCE.md`: exact commands, environment, dates, pass/fail results, benchmark and known issues.
- Working frontend, backend, viewer, DB, JSON/PDF exports and offline tests.

## 16. Definition of Done — do not claim 100% without evidence

- [ ] Fresh-clone setup works without paid credentials or GPU.
- [ ] A verified example UniProt accession loads metadata and an available structure.
- [ ] Valid mapped missense substitution produces a reproducible report.
- [ ] Invalid substitutions and mapping ambiguity are rejected accurately.
- [ ] 3D **wild-type** model and contacts are displayed correctly.
- [ ] Confidence and mutation-impact limitations are unmistakable.
- [ ] Analysis history persists across application restarts.
- [ ] JSON and PDF exports include provenance, methods, and cautions.
- [ ] All offline unit/integration tests pass.
- [ ] Frontend build and browser E2E tests pass.
- [ ] Network failure and unavailable structure are handled gracefully.
- [ ] No fabricated mutant geometry, clinical claims, fake scores, or fake test results.
- [ ] Setup, scientific assumptions, external terms, and remaining limitations are documented.

## 17. First instruction to the coding agent

**Begin now.** Read `AGENTS.md`, inspect the repository, and create `docs/PLAN.md` with actionable tasks, owners, dependencies, and acceptance tests. Verify official external API and Mol* integration details before coding adapters. Scaffold a runnable backend/frontend and implement the offline scientific engine first. Proceed phase by phase without requesting routine approvals. After each phase, run its gate and record actual results. If a gate fails, fix it before advancing. At completion, report exactly what is verified, what remains untested, how to launch the app, and any scientific limitations. Never substitute a polished mockup for a functioning system.
