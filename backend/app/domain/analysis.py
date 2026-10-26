from __future__ import annotations

import math
from typing import Any

from app.domain.contacts import ca_neighbors, heavy_atom_contacts
from app.domain.errors import InvalidParameters
from app.domain.mapping import build_mapping
from app.domain.models import AnalysisParameters, ProteinInfo, StructureInfo
from app.domain.properties import property_deltas
from app.domain.structure import ParsedStructure, confidence_band
from app.domain.variant import parse_variant

CA_RADIUS_MIN = 4.0
CA_RADIUS_MAX = 20.0
HEAVY_RADIUS_MIN = 2.0
HEAVY_RADIUS_MAX = 10.0


def validate_parameters(
    ca_radius_angstrom: float = 8.0,
    heavy_atom_radius_angstrom: float = 5.0,
) -> AnalysisParameters:
    for name, value in (
        ("ca_radius_angstrom", ca_radius_angstrom),
        ("heavy_atom_radius_angstrom", heavy_atom_radius_angstrom),
    ):
        if not isinstance(value, int | float) or not math.isfinite(float(value)):
            raise InvalidParameters(f"{name} must be a finite number.", details={"parameter": name})
    if not CA_RADIUS_MIN <= float(ca_radius_angstrom) <= CA_RADIUS_MAX:
        raise InvalidParameters(
            f"ca_radius_angstrom must be between {CA_RADIUS_MIN} and {CA_RADIUS_MAX}.",
            details={"parameter": "ca_radius_angstrom", "min": CA_RADIUS_MIN, "max": CA_RADIUS_MAX},
        )
    if not HEAVY_RADIUS_MIN <= float(heavy_atom_radius_angstrom) <= HEAVY_RADIUS_MAX:
        raise InvalidParameters(
            f"heavy_atom_radius_angstrom must be between {HEAVY_RADIUS_MIN} and {HEAVY_RADIUS_MAX}.",
            details={
                "parameter": "heavy_atom_radius_angstrom",
                "min": HEAVY_RADIUS_MIN,
                "max": HEAVY_RADIUS_MAX,
            },
        )
    return AnalysisParameters(
        ca_radius_angstrom=float(ca_radius_angstrom),
        heavy_atom_radius_angstrom=float(heavy_atom_radius_angstrom),
    )


def _confidence_payload(structure: ParsedStructure, target_index: int) -> dict[str, Any]:
    residue = structure.residue_by_index(target_index)
    value = residue.plddt_like
    if structure.confidence_source == "plddt":
        band = confidence_band(value)
        return {
            "source": "AlphaFold pLDDT",
            "availability": "available" if value is not None else "not_available",
            "per_residue_value": round(value, 2) if value is not None else None,
            "band": band,
            "semantics": (
                "pLDDT estimates local confidence in the wild-type predicted structure. "
                "It is not a prediction of mutation effect, stability, or pathogenicity."
            ),
            "note": "For AlphaFold models the per-residue CA B-factor field stores pLDDT.",
        }
    if structure.confidence_source == "b_factor":
        return {
            "source": "Experimental B-factor",
            "availability": "b_factor_only",
            "per_residue_value": round(value, 2) if value is not None else None,
            "band": None,
            "semantics": (
                "The B-factor of an experimental structure is not pLDDT and is not interpreted here "
                "as confidence in the model or in a mutation outcome."
            ),
            "note": "pLDDT: not available for experimental structures.",
        }
    return {
        "source": "Confidence",
        "availability": "not_available",
        "per_residue_value": None,
        "band": None,
        "semantics": "No per-residue confidence values were found in this structure.",
        "note": "Confidence: not available.",
    }


def _observations(
    protein: ProteinInfo,
    structure: StructureInfo,
    variant_text: str,
    target_label: str,
    mutation_label: str,
    ca_count: int,
    contact_count: int,
    parameters: AnalysisParameters,
) -> list[str]:
    model_kind = "predicted" if structure.is_predicted else "experimental"
    return [
        (
            f"In the supplied {model_kind} wild-type structure ({structure.source}, chain "
            f"{structure.chain}), residue {target_label} of {protein.accession} has "
            f"{ca_count} CA neighbour(s) within {parameters.ca_radius_angstrom:g} Å."
        ),
        (
            f"Its residue has {contact_count} other residue(s) with at least one heavy-atom pair within "
            f"{parameters.heavy_atom_radius_angstrom:g} Å."
        ),
        (
            f"The substitution {mutation_label} is analysed only for wild-type structural context and "
            "coarse physicochemical property differences."
        ),
    ]


def _cautions() -> list[str]:
    return [
        "This report does not establish a changed contact network, stability change, binding disruption, "
        "pathogenicity, or any observed mutant effect.",
        "The 3D coordinates are the wild-type reference model. No mutant structure was modelled "
        "or predicted.",
        "CA neighbours and heavy-atom contacts are geometric descriptors, not hydrogen bonds, salt bridges, "
        "or energetic couplings.",
        "pLDDT, when shown, is confidence in the wild-type predicted local structure, not mutation-outcome "
        "confidence.",
        "Research and education only. Not for clinical decision-making.",
    ]


def run_analysis(
    *,
    protein: ProteinInfo,
    structure: ParsedStructure,
    structure_info: StructureInfo,
    variant_text: str,
    parameters: AnalysisParameters,
    schema_version: str,
    algorithm_version: str,
    generated_at: str,
    max_contact_rows: int = 500,
) -> dict[str, Any]:
    variant = parse_variant(variant_text, protein.sequence)
    mapping = build_mapping(protein.sequence, structure, variant.position)
    target = structure.residue_by_index(mapping.structure_index)

    neighbors, neighbor_warnings = ca_neighbors(
        structure,
        mapping.structure_index,
        parameters.ca_radius_angstrom,
        structure_to_canonical=mapping.structure_to_canonical,
        max_rows=max_contact_rows,
    )
    contacts, contact_warnings = heavy_atom_contacts(
        structure,
        mapping.structure_index,
        parameters.heavy_atom_radius_angstrom,
        structure_to_canonical=mapping.structure_to_canonical,
        max_rows=max_contact_rows,
    )

    properties = property_deltas(variant.wt, variant.mutant)
    target_props = properties["wild_type"]
    confidence = _confidence_payload(structure, mapping.structure_index)
    warnings: list[str] = []
    warnings.extend(structure.warnings)
    warnings.extend(mapping.warnings)
    warnings.extend(neighbor_warnings)
    warnings.extend(contact_warnings)
    if not structure.is_predicted:
        warnings.append("The structure is not an AlphaFold prediction; pLDDT is not available.")

    mutation_label = f"{protein.name} {variant.wt}{variant.position}{variant.mutant}"
    target_label = f"{target.resname}{target.residue_id} (canonical {variant.position})"
    observations = _observations(
        protein,
        structure_info,
        variant.normalized,
        target_label,
        mutation_label,
        len(neighbors),
        len(contacts),
        parameters,
    )

    return {
        "schema_version": schema_version,
        "algorithm_version": algorithm_version,
        "generated_at": generated_at,
        "input": {
            "accession": protein.accession,
            "variant": variant.normalized,
            "variant_input": variant.input,
            "parameters": parameters.to_dict(),
        },
        "protein": {
            "accession": protein.accession,
            "name": protein.name,
            "organism": protein.organism,
            "gene": protein.gene,
            "length": protein.length,
        },
        "structure": {
            **structure_info.to_dict(),
            "coverage": {
                "structure_residues": len(structure.residues),
                "canonical_length": protein.length,
                "observed_sequence_length": len(structure.sequence),
            },
        },
        "mapping": mapping.to_dict(),
        "variant": {
            "normalized": variant.normalized,
            "wild_type": variant.wt,
            "position": variant.position,
            "mutant": variant.mutant,
            "wild_type_three_letter": target_props["three_letter"],
            "mutant_three_letter": properties["mutant"]["three_letter"],
        },
        "residue": {
            "structure_residue_id": target.residue_id,
            "resname": target.resname,
            "one_letter": target.one_letter,
            "ca_present": target.ca is not None,
            "heavy_atom_count": len(target.heavy_atoms),
        },
        "confidence": confidence,
        "properties": properties,
        "neighborhood": {
            "ca_neighbors": {
                "radius_angstrom": parameters.ca_radius_angstrom,
                "count": len(neighbors),
                "truncated": bool(neighbor_warnings),
                "rows": [row.to_dict() for row in neighbors],
            },
            "heavy_atom_contacts": {
                "radius_angstrom": parameters.heavy_atom_radius_angstrom,
                "count": len(contacts),
                "truncated": bool(contact_warnings),
                "rows": [row.to_dict() for row in contacts],
            },
        },
        "interpretation": {
            "observations": observations,
            "descriptors": [
                f"Residue category changes from {properties['wild_type']['category']} to "
                f"{properties['mutant']['category']}."
                if properties["deltas"]["category_changed"]
                else "Residue category is unchanged.",
                f"Charge class changes from {properties['wild_type']['charge_class']} to "
                f"{properties['mutant']['charge_class']}."
                if properties["deltas"]["charge_class_changed"]
                else "Charge class is unchanged.",
                f"Hydropathy delta (Kyte-Doolittle, mutant minus wild type): "
                f"{properties['deltas']['hydropathy']:+.2f}.",
            ],
            "cautions": _cautions(),
        },
        "warnings": warnings,
        "provenance": {
            "mode": protein.mode,
            "protein_source": {
                "name": "UniProt REST",
                "url": protein.source_url,
                "retrieved_at": protein.retrieved_at,
                "source_version": protein.source_version,
            },
            "structure_source": {
                "name": structure_info.source,
                "url": structure_info.url,
                "retrieved_at": structure_info.retrieved_at,
                "model_version": structure_info.model_version,
                "checksum_sha256": structure_info.checksum_sha256,
                "tool_used": structure_info.tool_used,
            },
            "mapping_method": "global sequence alignment; identity and coverage validated",
            "parameters": parameters.to_dict(),
            "algorithm_version": algorithm_version,
            "schema_version": schema_version,
        },
    }
