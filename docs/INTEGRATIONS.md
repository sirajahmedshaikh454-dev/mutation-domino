# Integrations

## UniProt REST
- Base URL default: `https://rest.uniprot.org`
- Adapter endpoint: `{base}/uniprotkb/{accession}.json`
- Used for canonical accession, protein name, organism, gene, canonical sequence, length, source/version metadata.
- Terms: UniProt REST API. No API key required. Identify via User-Agent.

## AlphaFold Protein Structure Database
- Base URL default: `https://alphafold.ebi.ac.uk`
- Metadata endpoint: `{base}/api/prediction/{accession}`
- Structure download URL taken from metadata fields `cifUrl`/`pdbUrl` (preferred mmCIF).
- Allowed hosts for structure download: `alphafold.ebi.ac.uk`.
- Terms: AlphaFold DB. Not all UniProt accessions have predictions; missing predictions return `STRUCTURE_UNAVAILABLE`.
- pLDDT is read from CA B-factor-like field only after source is confirmed AlphaFold.

## Fixture mode
- `MUTATION_DOMINO_MODE=fixture` serves recorded P69905 payloads from `backend/tests/fixtures` for offline dev/tests/E2E.
- Provenance records mode as `fixture`.

## Mol*
- Frontend lazy-loads `/molstar/molstar.js` and `/molstar/molstar.css` copied from installed npm package via `npm run prepare:molstar`.
- WebGL required; fallback UI otherwise.