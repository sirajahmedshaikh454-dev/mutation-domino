from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
AMINO_ACID_SET = set(AMINO_ACIDS)

THREE_TO_ONE: dict[str, str] = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}
ONE_TO_THREE = {v: k for k, v in THREE_TO_ONE.items()}

# Kyte & Doolittle (1982) hydropathy scale.
HYDROPATHY: dict[str, float] = {
    "A": 1.8,
    "R": -4.5,
    "N": -3.5,
    "D": -3.5,
    "C": 2.5,
    "Q": -3.5,
    "E": -3.5,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "L": 3.8,
    "K": -3.9,
    "M": 1.9,
    "F": 2.8,
    "P": -1.6,
    "S": -0.8,
    "T": -0.7,
    "W": -0.9,
    "Y": -1.3,
    "V": 4.2,
}

# Average residue masses in Da (free amino acid minus water), rounded to 2 decimals.
RESIDUE_MASS: dict[str, float] = {
    "A": 71.08,
    "R": 156.19,
    "N": 114.10,
    "D": 115.09,
    "C": 103.14,
    "Q": 128.13,
    "E": 129.12,
    "G": 57.05,
    "H": 137.14,
    "I": 113.16,
    "L": 113.16,
    "K": 128.17,
    "M": 131.19,
    "F": 147.18,
    "P": 97.12,
    "S": 87.08,
    "T": 101.10,
    "W": 186.21,
    "Y": 163.18,
    "V": 99.13,
}

CATEGORY: dict[str, str] = {
    "A": "hydrophobic",
    "V": "hydrophobic",
    "I": "hydrophobic",
    "L": "hydrophobic",
    "M": "hydrophobic",
    "F": "aromatic",
    "W": "aromatic",
    "Y": "aromatic",
    "S": "polar",
    "T": "polar",
    "N": "polar",
    "Q": "polar",
    "C": "polar",
    "K": "basic",
    "R": "basic",
    "H": "basic",
    "D": "acidic",
    "E": "acidic",
    "G": "special",
    "P": "special",
}

CHARGE_CLASS: dict[str, str] = {
    "K": "positive",
    "R": "positive",
    "D": "negative",
    "E": "negative",
    "H": "positive",
}
SIDECHAIN_HEAVY_ATOMS: dict[str, int] = {
    "G": 0,
    "A": 1,
    "S": 2,
    "C": 2,
    "P": 3,
    "V": 3,
    "T": 3,
    "L": 4,
    "I": 4,
    "N": 4,
    "D": 4,
    "M": 4,
    "Q": 5,
    "E": 5,
    "K": 5,
    "F": 6,
    "H": 6,
    "R": 7,
    "Y": 7,
    "W": 10,
}
AROMATIC = {"F", "W", "Y", "H"}
POLAR = {"S", "T", "N", "Q", "C", "Y", "H", "K", "R", "D", "E", "W"}

PROPERTY_TABLE_VERSION = "1.0.0"
PROPERTY_TABLE_SOURCE = (
    "Static coarse descriptors: Kyte & Doolittle (1982) hydropathy; average residue masses; "
    "manual side-chain heavy-atom counts. Not energy, stability, or function predictions."
)


@dataclass(frozen=True)
class ResidueProperties:
    one_letter: str
    three_letter: str
    category: str
    charge_class: str
    aromatic: bool
    polar_side_chain: bool
    hydropathy: float
    residue_mass_da: float
    sidechain_heavy_atoms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def residue_properties(one_letter: str) -> ResidueProperties:
    if one_letter not in AMINO_ACID_SET:
        raise ValueError(f"Unsupported amino acid: {one_letter!r}")
    return ResidueProperties(
        one_letter=one_letter,
        three_letter=ONE_TO_THREE[one_letter],
        category=CATEGORY[one_letter],
        charge_class=CHARGE_CLASS.get(one_letter, "neutral"),
        aromatic=one_letter in AROMATIC,
        polar_side_chain=one_letter in POLAR,
        hydropathy=HYDROPATHY[one_letter],
        residue_mass_da=RESIDUE_MASS[one_letter],
        sidechain_heavy_atoms=SIDECHAIN_HEAVY_ATOMS[one_letter],
    )


def property_deltas(wt: str, mutant: str) -> dict[str, Any]:
    wt_props = residue_properties(wt)
    mut_props = residue_properties(mutant)
    changes = {
        "category": {
            "from": wt_props.category,
            "to": mut_props.category,
            "changed": wt_props.category != mut_props.category,
        },
        "charge_class": {
            "from": wt_props.charge_class,
            "to": mut_props.charge_class,
            "changed": wt_props.charge_class != mut_props.charge_class,
        },
        "aromatic": {
            "from": wt_props.aromatic,
            "to": mut_props.aromatic,
            "changed": wt_props.aromatic != mut_props.aromatic,
        },
        "polar_side_chain": {
            "from": wt_props.polar_side_chain,
            "to": mut_props.polar_side_chain,
            "changed": wt_props.polar_side_chain != mut_props.polar_side_chain,
        },
    }
    return {
        "wild_type": wt_props.to_dict(),
        "mutant": mut_props.to_dict(),
        "deltas": {
            "hydropathy": round(mut_props.hydropathy - wt_props.hydropathy, 2),
            "residue_mass_da": round(mut_props.residue_mass_da - wt_props.residue_mass_da, 2),
            "sidechain_heavy_atoms": mut_props.sidechain_heavy_atoms - wt_props.sidechain_heavy_atoms,
            "category_changed": wt_props.category != mut_props.category,
            "charge_class_changed": wt_props.charge_class != mut_props.charge_class,
            "aromatic_changed": wt_props.aromatic != mut_props.aromatic,
        },
        "changes": changes,
        "table": {"version": PROPERTY_TABLE_VERSION, "source": PROPERTY_TABLE_SOURCE},
    }
