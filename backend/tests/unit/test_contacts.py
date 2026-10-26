from __future__ import annotations

import pytest

from app.domain.contacts import ca_neighbors, heavy_atom_contacts
from app.domain.structure import parse_structure_file
from tests.conftest import residue, write_pdb


@pytest.fixture()
def simple_structure(tmp_path):
    pdb = write_pdb(
        tmp_path / "simple.pdb",
        [
            residue(1, "ALA", 0.0),
            residue(2, "VAL", 5.0),
            residue(3, "GLY", 20.0),
        ],
    )
    return parse_structure_file(pdb, source="experimental")


def test_ca_neighbor_distance_filter(simple_structure) -> None:
    rows, warnings = ca_neighbors(simple_structure, 0, 8.0)
    assert [r.one_letter for r in rows] == ["V"]
    assert rows[0].distance_angstrom == pytest.approx(5.0)
    assert rows[0].category == "ca_neighbor"
    assert warnings == []


def test_ca_neighbor_excludes_self(simple_structure) -> None:
    rows, _ = ca_neighbors(simple_structure, 0, 100.0)
    assert all(row.structure_index != 0 for row in rows)
    assert len(rows) == 2


def test_heavy_atom_contact_distance(simple_structure) -> None:
    rows, _ = heavy_atom_contacts(simple_structure, 0, 5.1)
    assert [r.one_letter for r in rows] == ["V"]
    assert rows[0].distance_angstrom <= 5.1
    assert rows[0].category == "heavy_atom_contact"
    assert rows[0].target_atom is not None
    assert rows[0].partner_atom is not None


def test_heavy_atom_contacts_exclude_hydrogen(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "hydrogen_contact.pdb",
        [
            residue(
                1,
                "ALA",
                atoms=[("N", "N", 0.0, 0.0, 0.0), ("CA", "C", 0.0, 1.0, 0.0), ("C", "C", 0.0, 2.0, 0.0)],
            ),
            residue(
                2,
                "GLY",
                10.0,
                atoms=[
                    ("N", "N", 10.0, 0.0, 0.0),
                    ("CA", "C", 10.0, 1.0, 0.0),
                    ("HA", "H", 0.4, 0.0, 0.0),
                    ("C", "C", 10.0, 2.0, 0.0),
                ],
            ),
        ],
    )
    structure = parse_structure_file(pdb, source="experimental")
    rows, _ = heavy_atom_contacts(structure, 0, 1.0)
    assert rows == []


def test_canonical_positions_are_attached(tmp_path) -> None:
    pdb = write_pdb(tmp_path / "canonical.pdb", [residue(1, "ALA"), residue(2, "VAL", 5.0)])
    structure = parse_structure_file(pdb, source="experimental")
    rows, _ = ca_neighbors(structure, 0, 8.0, structure_to_canonical={1: 1})
    assert rows[0].canonical_position == 2
    assert rows[0].to_dict()["canonical_position"] == 2


def test_missing_ca_returns_warning(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "missing_ca.pdb",
        [
            residue(
                1,
                "ALA",
                atoms=[("N", "N", 0.0, 0.0, 0.0), ("C", "C", 0.0, 2.0, 0.0), ("O", "O", 0.0, 3.0, 0.0)],
            )
        ],
    )
    structure = parse_structure_file(pdb, source="experimental")
    rows, warnings = ca_neighbors(structure, 0, 8.0)
    assert rows == []
    assert warnings
    rows, warnings = heavy_atom_contacts(structure, 0, 5.0)
    assert rows == []
    assert warnings == []


def test_truncation_warning(tmp_path) -> None:
    residues = [residue(1, "ALA")]
    residues += [residue(i + 2, "VAL", 3.0) for i in range(5)]
    pdb = write_pdb(tmp_path / "many.pdb", residues)
    structure = parse_structure_file(pdb, source="experimental")
    rows, warnings = ca_neighbors(structure, 0, 10.0, max_rows=2)
    assert len(rows) == 2
    assert any("truncated" in warning for warning in warnings)
