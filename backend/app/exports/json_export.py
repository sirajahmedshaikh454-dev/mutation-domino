from __future__ import annotations

import json

from app.core.time import utc_now_iso
from app.persistence.repositories import AnalysisRecord

EXPORT_SCHEMA_VERSION = "1.0.0"


def build_json_export(record: AnalysisRecord) -> bytes:
    payload = {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": utc_now_iso(),
        "disclaimer": (
            "Mutation Domino reports wild-type structural context and coarse descriptors only. "
            "It is not a clinical or pathogenicity predictor and does not model the mutant structure."
        ),
        "analysis": record.envelope(),
        "methodology": {
            "algorithm_version": record.algorithm_version,
            "schema_version": record.schema_version,
            "parameters": record.parameters,
            "mapping_method": "global pairwise sequence alignment with identity and coverage validation",
            "contact_definitions": {
                "ca_neighbors": "C-alpha distance <= configured radius (default 8.0 Angstrom)",
                "heavy_atom_contacts": (
                    "minimum non-hydrogen atom distance <= configured radius (default 5.0 Angstrom)"
                ),
            },
            "confidence": (
                "pLDDT is reported only for AlphaFold models and describes confidence in the wild-type "
                "predicted local structure, not mutation outcomes. Experimental B-factors are not pLDDT."
            ),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
