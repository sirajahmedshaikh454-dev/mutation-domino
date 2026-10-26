# Mutation Domino

Research/education only. Not for clinical decision-making. No mutant 3D structure is generated.

## Prerequisites
- Python 3.11+
- Node.js LTS

## Backend setup (Windows PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy ..\.env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

## Backend setup (Unix)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

## Frontend setup
```bash
cd frontend
npm install
npm run dev
```

## Tests
```bash
cd backend && python -m pytest
cd backend && ruff check . && ruff format --check .
cd frontend && npm run lint && npm run typecheck && npm run test -- --run && npm run build
```

## Example walkthrough
1. Open http://localhost:5173
2. Search accession P69905.
3. Select a residue in the sequence, choose mutant, analyze.
4. Inspect wild-type 3D viewer, contacts, confidence, properties.
5. Save/reopen from History; export JSON/PDF.

## Fixture mode (offline)
Set `MUTATION_DOMINO_MODE=fixture` to serve recorded P69905 data.