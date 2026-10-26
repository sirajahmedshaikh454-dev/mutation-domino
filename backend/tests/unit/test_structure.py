from __future__ import annotations

import pytest

from app.domain.errors import MalformedStructure
from app.domain.structure import confidence_band, parse_structure_file
from tests.conftest import residue, write_pdb


def test_parses_alphafold_fixture(alphafold_structure) -> None:
    assert alphafold_structure.chain_id == "A"
    assert len(alphafold_structure.residues) == 142
    assert alphafold_structure.sequence.startswith("MVLSPADK")
    assert alphafold_structure.confidence_source == "plddt"
    first = alphafold_structure.residues[0]
    assert first.resname == "MET"
    assert first.ca is not None
    assert first.ca.bfactor == pytest.approx(65.38, abs=0.01)


def test_altloc_highest_occupancy_wins(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "altloc.pdb",
        [
            residue(
                1,
                atoms=[
                    ("N", "N", 0.0, 0.0, 0.0),
                    ("CA", "C", 0.0, 1.0, 0.0, "A", 0.40, 50.0),
                    ("CA", "C", 9.0, 1.0, 0.0, "B", 0.60, 60.0),
                    ("C", "C", 0.0, 2.0, 0.0),
                    ("O", "O", 0.0, 3.0, 0.0),
                ],
            )
        ],
    )
    parsed = parse_structure_file(pdb, source="experimental")
    ca = parsed.residues[0].ca
    assert ca is not None
    assert ca.x == pytest.approx(9.0)
    assert ca.altloc == "B"


def test_altloc_tie_prefers_lexicographic(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "altloc_tie.pdb",
        [
            residue(
                1,
                atoms=[
                    ("N", "N", 0.0, 0.0, 0.0),
                    ("CA", "C", 5.0, 1.0, 0.0, "B", 0.50, 50.0),
                    ("CA", "C", 1.0, 1.0, 0.0, "A", 0.50, 50.0),
                    ("C", "C", 0.0, 2.0, 0.0),
                    ("O", "O", 0.0, 3.0, 0.0),
                ],
            )
        ],
    )
    parsed = parse_structure_file(pdb, source="experimental")
    ca = parsed.residues[0].ca
    assert ca is not None
    assert ca.x == pytest.approx(1.0)
    assert ca.altloc == "A"


def test_hydrogens_are_retained_but_counted(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "hydrogen.pdb",
        [
            residue(
                1,
                atoms=[
                    ("N", "N", 0.0, 0.0, 0.0),
                    ("CA", "C", 0.0, 1.0, 0.0),
                    ("HA", "H", 0.0, 1.5, 0.0),
                    ("C", "C", 0.0, 2.0, 0.0),
                    ("O", "O", 0.0, 3.0, 0.0),
                ],
            )
        ],
    )
    parsed = parse_structure_file(pdb, source="experimental")
    assert parsed.hydrogen_atoms_excluded == 1
    assert any("hydrogen" in w for w in parsed.warnings)
    assert len(parsed.residues[0].heavy_atoms) == 4


def test_insertion_codes_are_preserved(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "insertion.pdb",
        [residue(10, "ALA"), residue(10, "GLY", 5.0, icode="A"), residue(11, "SER", 10.0)],
    )
    parsed = parse_structure_file(pdb, source="experimental")
    assert [r.residue_id for r in parsed.residues] == ["10", "10A", "11"]


def test_missing_ca_is_reported(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "noca.pdb",
        [
            residue(
                1,
                atoms=[("N", "N", 0.0, 0.0, 0.0), ("C", "C", 0.0, 2.0, 0.0), ("O", "O", 0.0, 3.0, 0.0)],
            )
        ],
    )
    parsed = parse_structure_file(pdb, source="experimental")
    assert parsed.residues[0].ca is None


def test_multiple_chains_warn(tmp_path) -> None:
    lines = []
    for chain in ("A", "B"):
        lines.append(write_pdb(tmp_path / f"chain_{chain}.pdb", [residue(1, "ALA")], chain=chain).read_text())
    combined = ""
    serial = 1
    for block in lines:
        for line in block.splitlines():
            if line.startswith("ATOM"):
                line = f"{line[:6]}{serial:5d}{line[11:]}"
                serial += 1
            combined += line + "\n"
    path = tmp_path / "two_chains.pdb"
    path.write_text(combined)
    parsed = parse_structure_file(path, source="experimental")
    assert parsed.chain_id == "A"
    assert any("Multiple protein chains" in w for w in parsed.warnings)


def test_missing_chain_raises(tmp_path) -> None:
    pdb = write_pdb(tmp_path / "one.pdb", [residue(1)])
    with pytest.raises(MalformedStructure):
        parse_structure_file(pdb, chain_id="Z", source="experimental")


def test_unsupported_format_raises(tmp_path) -> None:
    path = tmp_path / "structure.xyz"
    path.write_text("hello")
    with pytest.raises(MalformedStructure):
        parse_structure_file(path)


def test_confidence_bands() -> None:
    assert confidence_band(95)["key"] == "very_high"
    assert confidence_band(80)["key"] == "confident"
    assert confidence_band(60)["key"] == "low"
    assert confidence_band(30)["key"] == "very_low"
    assert confidence_band(None) is None
