from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.domain.properties import residue_properties
from app.domain.structure import COMMON_ELEMENTS, ParsedStructure, ResidueRecord


@dataclass(frozen=True)
class ContactRow:
    structure_index: int
    chain_id: str
    sequence_id: int
    insertion_code: str
    residue_id: str
    resname: str
    one_letter: str
    canonical_position: int | None
    distance_angstrom: float
    category: str
    target_atom: str | None = None
    partner_atom: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "structure_index": self.structure_index,
            "chain_id": self.chain_id,
            "sequence_id": self.sequence_id,
            "insertion_code": self.insertion_code,
            "residue_id": self.residue_id,
            "resname": self.resname,
            "one_letter": self.one_letter,
            "canonical_position": self.canonical_position,
            "distance_angstrom": round(self.distance_angstrom, 2),
            "category": self.category,
            "properties": self.properties,
        }
        if self.target_atom is not None:
            payload["target_atom"] = self.target_atom
        if self.partner_atom is not None:
            payload["partner_atom"] = self.partner_atom
        return payload


def _contact_atoms(residue: ResidueRecord) -> list[Any]:
    return [
        atom for atom in residue.atoms if not atom.is_hydrogen and atom.element.upper() in COMMON_ELEMENTS
    ]


def _coords(residue: ResidueRecord) -> np.ndarray | None:
    atoms = _contact_atoms(residue)
    if not atoms:
        return None
    return np.array([[a.x, a.y, a.z] for a in atoms], dtype=np.float64)


def _row(
    residue: ResidueRecord,
    distance: float,
    canonical_position: int | None,
    category: str,
    *,
    target_atom: str | None = None,
    partner_atom: str | None = None,
) -> ContactRow:
    props = residue_properties(residue.one_letter)
    return ContactRow(
        structure_index=residue.index,
        chain_id=residue.chain_id,
        sequence_id=residue.sequence_id,
        insertion_code=residue.insertion_code,
        residue_id=residue.residue_id,
        resname=residue.resname,
        one_letter=residue.one_letter,
        canonical_position=canonical_position,
        distance_angstrom=distance,
        category=category,
        target_atom=target_atom,
        partner_atom=partner_atom,
        properties={
            "category": props.category,
            "charge_class": props.charge_class,
            "aromatic": props.aromatic,
            "hydropathy": props.hydropathy,
        },
    )


def ca_neighbors(
    structure: ParsedStructure,
    target_index: int,
    radius_angstrom: float,
    *,
    structure_to_canonical: dict[int, int] | None = None,
    max_rows: int = 500,
) -> tuple[list[ContactRow], list[str]]:
    target = structure.residue_by_index(target_index)
    warnings: list[str] = []
    if target.ca is None:
        return [], ["The target residue has no CA atom; CA-neighbor analysis is unavailable."]
    center = np.array([target.ca.x, target.ca.y, target.ca.z], dtype=np.float64)
    inverse = structure_to_canonical or {}
    rows: list[ContactRow] = []
    for residue in structure.residues:
        if residue.index == target_index or residue.ca is None:
            continue
        point = np.array([residue.ca.x, residue.ca.y, residue.ca.z], dtype=np.float64)
        distance = float(np.linalg.norm(point - center))
        if distance <= radius_angstrom:
            rows.append(
                _row(
                    residue,
                    distance,
                    _canonical(inverse, residue.index),
                    "ca_neighbor",
                    target_atom="CA",
                    partner_atom="CA",
                )
            )
    rows.sort(key=lambda row: (row.distance_angstrom, row.structure_index))
    if len(rows) > max_rows:
        warnings.append(f"CA-neighbor list truncated to {max_rows} of {len(rows)} rows.")
        rows = rows[:max_rows]
    return rows, warnings


def heavy_atom_contacts(
    structure: ParsedStructure,
    target_index: int,
    radius_angstrom: float,
    *,
    structure_to_canonical: dict[int, int] | None = None,
    max_rows: int = 500,
) -> tuple[list[ContactRow], list[str]]:
    target = structure.residue_by_index(target_index)
    target_atoms = _contact_atoms(target)
    warnings: list[str] = []
    if not target_atoms:
        return [], ["The target residue has no heavy atoms available for contact analysis."]
    center = np.array([[a.x, a.y, a.z] for a in target_atoms], dtype=np.float64)
    inverse = structure_to_canonical or {}
    rows: list[ContactRow] = []
    for residue in structure.residues:
        if residue.index == target_index:
            continue
        partner = _coords(residue)
        if partner is None:
            continue
        deltas = center[:, None, :] - partner[None, :, :]
        distances = np.linalg.norm(deltas, axis=2)
        flat_index = int(np.argmin(distances))
        target_atom_index, partner_atom_index = np.unravel_index(flat_index, distances.shape)
        distance = float(distances[target_atom_index, partner_atom_index])
        if distance <= radius_angstrom:
            atoms = _contact_atoms(residue)
            rows.append(
                _row(
                    residue,
                    distance,
                    _canonical(inverse, residue.index),
                    "heavy_atom_contact",
                    target_atom=target_atoms[target_atom_index].name,
                    partner_atom=atoms[partner_atom_index].name,
                )
            )
    rows.sort(key=lambda row: (row.distance_angstrom, row.structure_index))
    if len(rows) > max_rows:
        warnings.append(f"Heavy-atom contact list truncated to {max_rows} of {len(rows)} rows.")
        rows = rows[:max_rows]
    return rows, warnings


def _canonical(inverse: dict[int, int], structure_index: int) -> int | None:
    value = inverse.get(structure_index)
    return value + 1 if value is not None else None


def out_of_range_residues(structure: ParsedStructure, target_index: int, radius: float) -> list[int]:
    """Return structure indices farther than ``radius`` from the target CA (sanity/debug helper)."""
    target = structure.residue_by_index(target_index)
    if target.ca is None:
        return [r.index for r in structure.residues if r.index != target_index]
    center = np.array([target.ca.x, target.ca.y, target.ca.z])
    far: list[int] = []
    for residue in structure.residues:
        if residue.ca is None:
            continue
        distance = float(np.linalg.norm(np.array([residue.ca.x, residue.ca.y, residue.ca.z]) - center))
        if distance > radius:
            far.append(residue.index)
    return far
