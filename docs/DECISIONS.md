# Architecture Decisions

## ADR-001 — Monorepo: FastAPI backend + React/Vite frontend

Backend owns all biology. The browser only presents server-computed results and the
wild-type structure. Same-origin in production via static build served by FastAPI is
optional; development uses Vite's proxy to `http://127.0.0.1:8000`.

## ADR-002 — Deterministic scientific core is network-free

`app/domain/*` contains pure functions operating on validated dataclasses. Adapters
return data; they do not compute structure context. Every fixture test runs offline.

## ADR-003 — Sequence mapping by alignment, never offset arithmetic

The canonical UniProt sequence is globally aligned to the observed residue sequence of
the selected structure chain. A canonical position maps only if:

1. the aligned canonical residue equals the requested wild-type letter,
2. the aligned structure residue exists and has the same residue identity,
3. the position is covered by exactly one alignment column.

Mapping failures raise typed errors (`POSITION_UNMAPPED`, `AMBIGUOUS_MAPPING`,
`VARIANT_WT_MISMATCH`). Auth numbering and insertion codes are preserved as provenance;
they are never assumed equal to canonical numbering.

## ADR-004 — AlphaFold only in MVP

The MVP uses AlphaFold DB predictions. Experimental PDB support is explicitly deferred.
Structure downloads are restricted to the AlphaFold host from a validated metadata
response (no arbitrary URL proxy). SHA-256, timestamp, model version, and source URL are
persisted.

## ADR-005 — Confidence semantics

For AlphaFold, CA B-factor is interpreted as pLDDT only after the model source is
confirmed as AlphaFold. For experimental structures, B-factors are shown as
"B-factor (experimental)" and pLDDT is `not available`.

## ADR-006 — Altloc and hydrogen policy

Parsing selects, per atom, the alternate location with the highest occupancy; ties are
resolved by lexicographically smallest altloc name. Hydrogen/deuterium atoms are
excluded from heavy-atom contacts but retained for parsing. Unknown elements are
excluded from contacts and reported as a warning.

## ADR-007 — Persistence: SQLite + SQLAlchemy 2 + Alembic

Analyses store normalized variant, parameters, result JSON, algorithm/schema version,
warnings, and provenance. The app auto-creates tables on first start for local
convenience; the Alembic baseline migration is separately tested against an empty DB.
SQLite is explicitly a single-instance local store, not a public multi-user backend.

## ADR-008 — Mol* viewer loading

Mol* is a heavy dependency. The frontend lazy-loads the official Mol* viewer bundle
(copied from the installed npm package into `public/molstar/`) only when the structure
viewer mounts. The viewer loads the same-origin structure endpoint, labels the view
"Wild-type reference structure", and highlights the target residue and neighbors via
selection. A visible fallback appears if WebGL or the bundle is unavailable.

## ADR-009 — No composite score

No pathogenicity or "domino" score is computed. Outputs are observations, coarse
descriptors, and cautions with thresholds visible.

## ADR-010 — Fixture mode

`MUTATION_DOMINO_MODE=fixture` makes the backend serve recorded P69905 AlphaFold/UniProt
responses for offline development, tests, and E2E. The mode is displayed in provenance
as `fixture` so a demo can never be mistaken for a live query.
