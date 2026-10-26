# Architecture

Frontend: React + TypeScript + Vite SPA. Backend: FastAPI + SQLAlchemy + SQLite. Backend owns scientific calculations and mapping. Frontend renders server results and wild-type structure via Mol*.

Data flow: accession -> UniProt adapter -> AlphaFold adapter -> cache -> mapping validation -> analysis engine -> SQLite -> JSON/PDF exports.

Key modules:
- `backend/app/domain/*`: pure scientific core (variant, structure, mapping, contacts, properties, analysis).
- `backend/app/integrations/*`: bounded HTTP, UniProt, AlphaFold, cache.
- `backend/app/services/*`: orchestration.
- `backend/app/persistence/*`: SQLite tables/repositories/migrations.
- `backend/app/exports/*`: JSON and PDF.
- `frontend/src`: pages, components, API client, types.