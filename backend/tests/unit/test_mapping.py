from __future__ import annotations

import pytest

from app.domain.errors import AmbiguousMapping, PositionUnmapped
from app.domain.mapping import build_mapping
from app.domain.structure import parse_structure_file
from tests.conftest import residue, write_pdb


def test_maps_hemoglobin_alpha_position(alphafold_structure, hemoglobin_sequence) -> None:
    mapping = build_mapping(hemoglobin_sequence, alphafold_structure, 10)
    assert mapping.structure_residue_id == "10"
    assert mapping.residue_name == "ASN"
    assert mapping.canonical_residue == "N"
    assert mapping.alignment["mismatches"] == 0
    assert mapping.alignment["coverage"] == 1.0
    assert mapping.mapping_status == "mapped"
    inverse = mapping.structure_to_canonical
    assert inverse[9] == 9


def test_missing_n_terminal_residues_shift_mapping(tmp_path) -> None:
    names = ["LEU", "SER", "PRO", "ALA", "ASP", "LYS"]
    pdb = write_pdb(
        tmp_path / "truncated.pdb",
        [residue(i + 3, names[i], float(i * 4)) for i in range(len(names))],
    )
    structure = parse_structure_file(pdb, source="experimental")
    canonical = "MVLSPADK"
    assert structure.sequence == "LSPADK"
    mapping = build_mapping(canonical, structure, 4)
    assert mapping.structure_residue_id == "4"
    assert mapping.structure_index == 1
    assert mapping.alignment["canonical_gap_columns"] == 2
    assert mapping.alignment["structure_gap_columns"] == 0


def test_missing_loop_creates_structure_gap(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "gap.pdb",
        [residue(1, "ALA"), residue(2, "GLY"), residue(6, "SER"), residue(7, "THR")],
    )
    structure = parse_structure_file(pdb, source="experimental")
    canonical = "AGKLPST"
    mapping = build_mapping(canonical, structure, 6)
    assert mapping.structure_residue_id == "6"
    assert mapping.alignment["canonical_gap_columns"] == 3
    assert mapping.alignment["structure_gap_columns"] == 0


def test_insertion_code_mapping(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "icode.pdb",
        [residue(1, "MET"), residue(2, "ALA"), residue(2, "LYS", 8.0, icode="A")],
    )
    structure = parse_structure_file(pdb, source="experimental")
    mapping = build_mapping("MAK", structure, 3)
    assert mapping.structure_residue_id == "2A"
    assert mapping.insertion_code == "A"
    assert mapping.structure_sequence_id == 2


def test_wt_mismatch_in_structure_raises(tmp_path) -> None:
    pdb = write_pdb(tmp_path / "mismatch.pdb", [residue(1, "ALA"), residue(2, "GLY"), residue(3, "SER")])
    structure = parse_structure_file(pdb, source="experimental")
    with pytest.raises(PositionUnmapped):
        build_mapping("AGK", structure, 3)


def test_missing_residue_position_is_unmapped(tmp_path) -> None:
    pdb = write_pdb(tmp_path / "short.pdb", [residue(1, "MET")])
    structure = parse_structure_file(pdb, source="experimental")
    with pytest.raises((PositionUnmapped, AmbiguousMapping)):
        build_mapping("MVLS", structure, 4)


def test_repeated_sequence_is_ambiguous(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "repeat.pdb",
        [residue(1, "ALA"), residue(2, "ALA")],
    )
    structure = parse_structure_file(pdb, source="experimental")
    with pytest.raises(AmbiguousMapping):
        build_mapping("AAA", structure, 1)


def test_missing_ca_blocks_mapping(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "noca.pdb",
        [
            residue(
                1,
                "ALA",
                atoms=[("N", "N", 0.0, 0.0, 0.0), ("C", "C", 0.0, 2.0, 0.0), ("O", "O", 0.0, 3.0, 0.0)],
            )
        ],
    )
    structure = parse_structure_file(pdb, source="experimental")
    with pytest.raises(PositionUnmapped, match="CA"):
        build_mapping("A", structure, 1)
