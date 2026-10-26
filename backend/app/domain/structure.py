from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from Bio.PDB import MMCIFParser, PDBParser
from Bio.PDB.Chain import Chain
from Bio.PDB.Residue import DisorderedResidue, Residue

from app.domain.errors import MalformedStructure, StructureTooLarge
from app.domain.properties import THREE_TO_ONE

HYDROGEN_ELEMENTS = {"H", "D"}
COMMON_ELEMENTS = {
    "C",
    "N",
    "O",
    "S",
    "P",
    "SE",
    "F",
    "CL",
    "BR",
    "I",
    "FE",
    "ZN",
    "MG",
    "CA",
    "MN",
    "CU",
    "NA",
    "K",
}
CONFIDENCE_BANDS = (
    (90.0, "very_high", "Very high (pLDDT > 90)"),
    (70.0, "confident", "Confident (70 < pLDDT <= 90)"),
    (50.0, "low", "Low (50 < pLDDT <= 70)"),
    (0.0, "very_low", "Very low (pLDDT <= 50)"),
)


@dataclass(frozen=True)
class AtomRecord:
    name: str
    element: str
    x: float
    y: float
    z: float
    altloc: str
    occupancy: float
    bfactor: float | None

    @property
    def is_hydrogen(self) -> bool:
        return self.element.upper() in HYDROGEN_ELEMENTS


@dataclass(frozen=True)
class ResidueRecord:
    index: int
    chain_id: str
    sequence_id: int
    insertion_code: str
    resname: str
    one_letter: str
    atoms: tuple[AtomRecord, ...]
    ca: AtomRecord | None
    mean_bfactor: float | None

    @property
    def residue_id(self) -> str:
        return f"{self.sequence_id}{self.insertion_code}".strip()

    @property
    def label(self) -> str:
        return f"{self.resname}{self.residue_id}"

    @property
    def heavy_atoms(self) -> tuple[AtomRecord, ...]:
        return tuple(a for a in self.atoms if not a.is_hydrogen)

    @property
    def plddt_like(self) -> float | None:
        if self.ca is None:
            return None
        return self.ca.bfactor


@dataclass(frozen=True)
class ParsedStructure:
    chain_id: str
    residues: tuple[ResidueRecord, ...]
    source: Literal["alphafold", "experimental", "unknown"]
    confidence_source: Literal["plddt", "b_factor", "none"]
    warnings: tuple[str, ...] = ()
    model_count: int = 1
    hydrogen_atoms_excluded: int = 0
    unknown_element_atoms: int = 0
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def is_predicted(self) -> bool:
        return self.source == "alphafold"

    @property
    def sequence(self) -> str:
        return "".join(r.one_letter for r in self.residues)

    def residue_by_index(self, index: int) -> ResidueRecord:
        return self.residues[index]


def confidence_band(value: float | None) -> dict[str, object] | None:
    if value is None:
        return None
    for threshold, key, label in CONFIDENCE_BANDS:
        if value > threshold:
            return {"key": key, "label": label, "threshold": threshold}
    return {"key": "very_low", "label": "Very low (pLDDT <= 50)", "threshold": 0.0}


def _guess_element(atom_name: str) -> str:
    letters = "".join(ch for ch in atom_name if ch.isalpha()).upper()
    if not letters:
        return "?"
    if letters[:2] in COMMON_ELEMENTS:
        return letters[:2]
    return letters[0]


def _atom_sort_key(atom: object) -> tuple[float, str]:
    altloc = str(getattr(atom, "get_altloc", lambda: " ")()).strip()
    occupancy = float(getattr(atom, "get_occupancy", lambda: 0.0)() or 0.0)
    return (-occupancy, altloc)


def _selected_atoms(residue: Residue) -> tuple[list[object], int]:
    grouped: dict[str, list[object]] = {}
    hydrogen_count = 0
    unknown_count = 0
    for atom in residue.get_atoms():
        variants = list(atom.disordered_get_list()) if atom.is_disordered() else [atom]  # type: ignore[attr-defined]
        for variant in variants:
            name = str(variant.get_name()).strip()
            grouped.setdefault(name, []).append(variant)
    chosen: list[object] = []
    for variants in grouped.values():
        variant = sorted(variants, key=_atom_sort_key)[0]
        element = (
            str(getattr(variant, "element", "") or "").strip() or _guess_element(str(variant.get_name()))
        ).upper()
        if element in HYDROGEN_ELEMENTS:
            hydrogen_count += 1
        elif element not in COMMON_ELEMENTS:
            unknown_count += 1
        chosen.append(variant)
    return chosen, hydrogen_count + unknown_count


def _choose_residue_conformer(residue: Residue) -> Residue:
    if not isinstance(residue, DisorderedResidue):
        return residue
    candidates = residue.get_unpacked_list()
    if not candidates:
        return residue

    def total_occupancy(candidate: Residue) -> tuple[float, str]:
        total = sum(float(a.get_occupancy() or 0.0) for a in candidate.get_atoms())
        altloc = str(candidate.id[0]).strip()
        return (-total, altloc)

    return sorted(candidates, key=total_occupancy)[0]


def _find_chain(model: object, chain_id: str | None) -> tuple[Chain, list[str]]:
    chains = list(model)  # type: ignore[attr-defined]
    warnings: list[str] = []
    if chain_id:
        for chain in chains:
            if chain.id == chain_id:
                return chain, warnings
        raise MalformedStructure(
            f"Chain {chain_id!r} was not found in the structure.",
            details={"requested_chain": chain_id, "available_chains": [c.id for c in chains]},
        )
    usable = [c for c in chains if any(r.id[0] == " " and r.resname in THREE_TO_ONE for r in c)]
    if not usable:
        raise MalformedStructure("The structure contains no standard protein residues.")
    if len(usable) > 1:
        warnings.append(
            "Multiple protein chains were found; analysing the first chain "
            f"{usable[0].id!r}. Chain selection is required for other chains."
        )
    return usable[0], warnings


def parse_structure_file(
    path: str | Path,
    *,
    chain_id: str | None = None,
    source: Literal["alphafold", "experimental", "unknown"] = "unknown",
    max_bytes: int | None = None,
    max_residues: int | None = None,
) -> ParsedStructure:
    structure_path = Path(path)
    if not structure_path.is_file():
        raise MalformedStructure("Structure file is missing.", details={"path": structure_path.name})
    size = structure_path.stat().st_size
    if max_bytes is not None and size > max_bytes:
        raise StructureTooLarge(
            "Structure file exceeds the configured size limit.",
            details={"bytes": size, "limit": max_bytes},
        )
    suffix = structure_path.suffix.lower()
    try:
        if suffix in {".cif", ".mmcif"}:
            parser = MMCIFParser(QUIET=True)
        elif suffix in {".pdb", ".ent"}:
            parser = PDBParser(QUIET=True)
        else:
            raise MalformedStructure(
                "Unsupported structure format. Expected .cif, .mmcif, or .pdb.",
                details={"suffix": suffix},
            )
        structure = parser.get_structure("model", str(structure_path))
    except MalformedStructure:
        raise
    except Exception as exc:
        raise MalformedStructure(
            "The structure file could not be parsed.",
            details={"reason": type(exc).__name__},
        ) from exc

    models = list(structure)
    if not models:
        raise MalformedStructure("The structure file contains no models.")
    model = models[0]
    chain, warnings = _find_chain(model, chain_id)

    residues: list[ResidueRecord] = []
    hydrogens = 0
    unknown_elements = 0
    skipped_resnames: set[str] = set()
    seen_ids: set[tuple[int, str]] = set()
    for residue in chain:
        if residue.id[0] != " " and not residue.is_disordered():
            continue
        resname = residue.resname.strip().upper()
        if resname not in THREE_TO_ONE:
            skipped_resnames.add(resname)
            continue
        chosen = _choose_residue_conformer(residue)
        sequence_id = int(chosen.id[1])
        insertion_code = str(chosen.id[2]).strip()
        key = (sequence_id, insertion_code)
        if key in seen_ids:
            raise MalformedStructure(
                "The structure contains duplicate residue identifiers on the selected chain.",
                details={"residue_id": f"{sequence_id}{insertion_code}", "chain": chain.id},
            )
        seen_ids.add(key)
        atoms_raw, excluded = _selected_atoms(chosen)
        hydrogens += sum(
            1
            for atom in atoms_raw
            if (
                str(getattr(atom, "element", "") or "").strip() or _guess_element(str(atom.get_name()))
            ).upper()
            in HYDROGEN_ELEMENTS
        )
        atoms: list[AtomRecord] = []
        for atom in atoms_raw:
            element = (
                str(getattr(atom, "element", "") or "").strip() or _guess_element(str(atom.get_name()))
            ).upper()
            if element not in COMMON_ELEMENTS and element not in HYDROGEN_ELEMENTS:
                unknown_elements += 1
            coord = atom.get_coord()
            occupancy = float(atom.get_occupancy() or 0.0)
            bfactor = atom.get_bfactor()
            atoms.append(
                AtomRecord(
                    name=str(atom.get_name()).strip(),
                    element=element,
                    x=float(coord[0]),
                    y=float(coord[1]),
                    z=float(coord[2]),
                    altloc=str(atom.get_altloc()).strip(),
                    occupancy=occupancy,
                    bfactor=float(bfactor) if bfactor is not None else None,
                )
            )
        ca = next((a for a in atoms if a.name == "CA"), None)
        heavy_bfactors = [a.bfactor for a in atoms if not a.is_hydrogen and a.bfactor is not None]
        residues.append(
            ResidueRecord(
                index=len(residues),
                chain_id=chain.id,
                sequence_id=sequence_id,
                insertion_code=insertion_code,
                resname=resname,
                one_letter=THREE_TO_ONE[resname],
                atoms=tuple(atoms),
                ca=ca,
                mean_bfactor=(sum(heavy_bfactors) / len(heavy_bfactors)) if heavy_bfactors else None,
            )
        )
        del excluded

    if not residues:
        raise MalformedStructure("No standard residues with atoms were found on the selected chain.")
    if max_residues is not None and len(residues) > max_residues:
        raise StructureTooLarge(
            "The structure has more residues than the configured analysis limit.",
            details={"residues": len(residues), "limit": max_residues},
        )

    if skipped_resnames:
        warnings.append("Non-standard residues were skipped: " + ", ".join(sorted(skipped_resnames)) + ".")
    if hydrogens:
        warnings.append(f"{hydrogens} hydrogen/deuterium atoms were ignored for heavy-atom contacts.")
    if unknown_elements:
        warnings.append(
            f"{unknown_elements} atoms had unrecognised elements and were excluded from contacts."
        )

    if source == "alphafold":
        confidence_source: Literal["plddt", "b_factor", "none"] = "plddt"
    elif any(a.bfactor is not None for r in residues for a in r.atoms):
        confidence_source = "b_factor"
    else:
        confidence_source = "none"

    return ParsedStructure(
        chain_id=chain.id,
        residues=tuple(residues),
        source=source,
        confidence_source=confidence_source,
        warnings=tuple(warnings),
        model_count=len(models),
        hydrogen_atoms_excluded=hydrogens,
        unknown_element_atoms=unknown_elements,
    )
