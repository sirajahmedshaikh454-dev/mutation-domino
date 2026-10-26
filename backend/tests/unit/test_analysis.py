from __future__ import annotations

import copy

import pytest

from app.domain.analysis import run_analysis, validate_parameters
from app.domain.errors import InvalidParameters, VariantWtMismatch
from app.domain.models import ProteinInfo, StructureInfo
from app.domain.structure import parse_structure_file
from tests.conftest import residue, write_pdb

PROTEIN = ProteinInfo(
    accession="P69905",
    name="Hemoglobin subunit alpha",
    organism="Homo sapiens",
    sequence=(
        "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHK"
        "LRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
    ),
    length=142,
    gene="HBA1",
    source_url="https://rest.uniprot.org/uniprotkb/P69905.json",
    retrieved_at="2026-10-25T00:00:00Z",
    source_version="2025_05",
    mode="fixture",
)

STRUCTURE_INFO = StructureInfo(
    accession="P69905",
    source="AlphaFold DB",
    model_version="v6",
    chain="A",
    url="https://alphafold.ebi.ac.uk/files/AF-P69905-F1-model_v6.cif",
    checksum_sha256="abc123",
    retrieved_at="2026-10-25T00:00:00Z",
    is_predicted=True,
    confidence_source="plddt",
    file_format="cif",
    file_size_bytes=137559,
    tool_used="AlphaFold Monomer v2.0 pipeline",
    model_created_date="2025-08-01T00:00:00Z",
    mode="fixture",
)


def _run(structure, variant="N10V", parameters=None):
    return run_analysis(
        protein=PROTEIN,
        structure=structure,
        structure_info=STRUCTURE_INFO,
        variant_text=variant,
        parameters=parameters or validate_parameters(),
        schema_version="1.0.0",
        algorithm_version="1.0.0",
        generated_at="2026-10-25T12:00:00Z",
    )


def test_hemoglobin_analysis_is_reproducible(alphafold_structure) -> None:
    first = _run(alphafold_structure)
    second = _run(alphafold_structure)
    assert first == second
    assert first["variant"]["normalized"] == "N10V"
    assert first["mapping"]["structure_residue_id"] == "10"
    assert first["mapping"]["mapping_status"] == "mapped"
    assert first["neighborhood"]["ca_neighbors"]["radius_angstrom"] == 8.0
    assert first["neighborhood"]["ca_neighbors"]["count"] > 0
    assert first["neighborhood"]["heavy_atom_contacts"]["count"] > 0
    assert first["confidence"]["availability"] == "available"
    assert first["confidence"]["per_residue_value"] is not None
    assert first["confidence"]["band"]["key"] in {"very_high", "confident", "low", "very_low"}
    assert any("not a mutation" in c or "not mutation" in c for c in first["interpretation"]["cautions"])
    assert first["structure"]["checksum_sha256"] == "abc123"
    assert first["provenance"]["mode"] == "fixture"


def test_analysis_rejects_wt_mismatch(alphafold_structure) -> None:
    with pytest.raises(VariantWtMismatch):
        _run(alphafold_structure, variant="K10V")


def test_analysis_rejects_bad_parameters(alphafold_structure) -> None:
    with pytest.raises(InvalidParameters):
        _run(alphafold_structure, parameters=validate_parameters(ca_radius_angstrom=100))


def test_experimental_bfactor_is_not_plddt(tmp_path) -> None:
    pdb = write_pdb(
        tmp_path / "exp.pdb",
        [residue(1, "MET"), residue(2, "VAL", 4.0), residue(3, "LEU", 7.0)],
    )
    structure = parse_structure_file(pdb, source="experimental")
    protein = ProteinInfo(
        accession="P69905",
        name="Test protein",
        organism="Homo sapiens",
        sequence="MVL",
        length=3,
        mode="fixture",
    )
    info = StructureInfo(
        accession="P69905",
        source="Experimental PDB",
        model_version="test",
        chain="A",
        url="",
        checksum_sha256="def456",
        retrieved_at="2026-10-25T00:00:00Z",
        is_predicted=False,
        confidence_source="b_factor",
        file_format="pdb",
        file_size_bytes=100,
    )
    result = run_analysis(
        protein=protein,
        structure=structure,
        structure_info=info,
        variant_text="M1V",
        parameters=validate_parameters(),
        schema_version="1.0.0",
        algorithm_version="1.0.0",
        generated_at="2026-10-25T12:00:00Z",
    )
    assert result["confidence"]["availability"] == "b_factor_only"
    assert result["confidence"]["band"] is None
    assert "not pLDDT" in result["confidence"]["semantics"]
    assert any("not an AlphaFold" in warning for warning in result["warnings"])
    assert result["structure"]["is_predicted"] is False


def test_analysis_result_has_no_mutant_geometry(alphafold_structure) -> None:
    result = _run(alphafold_structure)
    payload = copy.deepcopy(result)
    assert "mutant_structure" not in payload
    assert "domino_score" not in payload
    assert "pathogenicity" not in payload
