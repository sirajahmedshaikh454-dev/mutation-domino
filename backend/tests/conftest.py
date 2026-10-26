from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.structure import parse_structure_file

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def hemoglobin_metadata() -> dict:
    return json.loads((FIXTURES / "uniprot_P69905.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def hemoglobin_sequence(hemoglobin_metadata: dict) -> str:
    return hemoglobin_metadata["sequence"]["value"]


@pytest.fixture(scope="session")
def alphafold_metadata() -> dict:
    return json.loads((FIXTURES / "alphafold_P69905.json").read_text(encoding="utf-8"))[0]


@pytest.fixture(scope="session")
def alphafold_structure() -> object:
    return parse_structure_file(
        FIXTURES / "af_P69905.cif",
        chain_id="A",
        source="alphafold",
        max_bytes=30 * 1024 * 1024,
        max_residues=5000,
    )


def make_pdb(residues: list[dict], *, chain: str = "A") -> str:
    """Build a minimal PDB string from residue dictionaries.

    Each atom tuple is (name, element, x, y, z) plus optional (altloc, occupancy, bfactor).
    Each residue is {"seq": int, "icode": str, "name": str, "atoms": [...]}.
    """
    lines: list[str] = []
    serial = 1
    for residue in residues:
        resname = residue["name"]
        seq = residue["seq"]
        icode = residue.get("icode", "") or " "
        for atom in residue["atoms"]:
            name, element, x, y, z = atom[:5]
            altloc = atom[5] if len(atom) > 5 else " "
            occupancy = atom[6] if len(atom) > 6 else 1.0
            bfactor = atom[7] if len(atom) > 7 else 50.0
            element_field = f"{element:>2}"
            lines.append(
                f"ATOM  {serial:5d} {name:<4}{altloc:1}{resname:>3} {chain:1}{seq:4d}{icode:1}   "
                f"{x:8.3f}{y:8.3f}{z:8.3f}{occupancy:6.2f}{bfactor:6.2f}          {element_field:>2}  "
            )
            serial += 1
    lines.append("END")
    return "\n".join(lines) + "\n"


def write_pdb(path: Path, residues: list[dict], *, chain: str = "A") -> Path:
    path.write_text(make_pdb(residues, chain=chain), encoding="utf-8")
    return path


def residue(seq: int, name: str = "ALA", x: float = 0.0, *, icode: str = "", atoms=None) -> dict:
    if atoms is None:
        atoms = [
            ("N", "N", x, 0.0, 0.0),
            ("CA", "C", x, 1.0, 0.0),
            ("C", "C", x, 2.0, 0.0),
            ("O", "O", x, 3.0, 0.0),
            ("CB", "C", x, 1.0, 1.0),
        ]
    return {"seq": seq, "icode": icode, "name": name, "atoms": atoms}
