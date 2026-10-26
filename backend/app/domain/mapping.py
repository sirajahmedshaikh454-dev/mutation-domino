from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Bio import Align

from app.domain.errors import AmbiguousMapping, PositionUnmapped
from app.domain.structure import ParsedStructure

MAX_ENUMERATED_ALIGNMENTS = 16


@dataclass(frozen=True)
class ResidueMapping:
    canonical_position: int
    canonical_residue: str
    structure_index: int
    structure_chain: str
    structure_residue_id: str
    structure_sequence_id: int
    insertion_code: str
    residue_name: str
    residue_three_letter: str
    mapping_status: str
    canonical_to_structure: dict[int, int] = field(default_factory=dict)
    structure_to_canonical: dict[int, int] = field(default_factory=dict)
    alignment: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_position": self.canonical_position,
            "canonical_residue": self.canonical_residue,
            "structure_chain": self.structure_chain,
            "structure_residue_id": self.structure_residue_id,
            "structure_sequence_id": self.structure_sequence_id,
            "insertion_code": self.insertion_code,
            "residue_name": self.residue_name,
            "residue_three_letter": self.residue_three_letter,
            "mapping_status": self.mapping_status,
            "alignment": self.alignment,
            "warnings": list(self.warnings),
        }


def _aligner() -> Align.PairwiseAligner:
    aligner = Align.PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2.0
    aligner.mismatch_score = -1.0
    aligner.open_gap_score = -10.0
    aligner.extend_gap_score = -0.5
    return aligner


def _block_positions(alignment: Align.Alignment) -> dict[int, int]:
    """Map 0-based canonical positions to 0-based structure residue indices for one alignment."""
    target_blocks, query_blocks = alignment.aligned
    mapping: dict[int, int] = {}
    for (t_start, t_end), (q_start, q_end) in zip(target_blocks, query_blocks, strict=True):
        length = int(t_end - t_start)
        if length != int(q_end - q_start):
            raise AmbiguousMapping("Alignment produced blocks of unequal length.")
        for offset in range(length):
            mapping[int(t_start) + offset] = int(q_start) + offset
    return mapping


def build_mapping(
    canonical_sequence: str,
    structure: ParsedStructure,
    target_position: int,
) -> ResidueMapping:
    if not canonical_sequence:
        raise PositionUnmapped("The canonical sequence is empty.")
    if target_position < 1 or target_position > len(canonical_sequence):
        raise PositionUnmapped(
            "The requested position is outside the canonical sequence.",
            details={"position": target_position, "length": len(canonical_sequence)},
        )
    observed = structure.sequence
    if not observed:
        raise PositionUnmapped("The selected structure chain contains no usable residues.")

    target_index = target_position - 1
    canonical_residue = canonical_sequence[target_index]
    alignments = _aligner().align(canonical_sequence, observed)
    total = len(alignments)
    sampled: list[Align.Alignment] = []
    for index, alignment in enumerate(alignments):
        if index >= MAX_ENUMERATED_ALIGNMENTS:
            break
        sampled.append(alignment)
    if not sampled:
        raise PositionUnmapped("No global alignment between the canonical sequence and the structure.")

    candidate_targets: set[int | None] = set()
    for alignment in sampled:
        mapping = _block_positions(alignment)
        candidate_targets.add(mapping.get(target_index))
    if len(candidate_targets) > 1 or None in candidate_targets:
        raise AmbiguousMapping(
            "The requested residue does not map unambiguously to the selected structure chain.",
            details={
                "position": target_position,
                "candidate_structure_indices": sorted(i for i in candidate_targets if i is not None),
                "optimal_alignments": total,
            },
        )

    structure_index = next(iter(candidate_targets))
    assert structure_index is not None
    primary = sampled[0]
    mapping = _block_positions(primary)
    if mapping.get(target_index) != structure_index:
        for alignment in sampled[1:]:
            candidate = _block_positions(alignment)
            if candidate.get(target_index) == structure_index:
                mapping = candidate
                break

    aligned_pairs = sorted(mapping.items())
    identities = sum(
        1
        for canonical_index, structure_position in aligned_pairs
        if canonical_sequence[canonical_index] == observed[structure_position]
    )
    mismatches = len(aligned_pairs) - identities
    canonical_gap_columns = len(canonical_sequence) - len(aligned_pairs)
    structure_gap_columns = len(observed) - len(aligned_pairs)
    coverage = len(aligned_pairs) / len(canonical_sequence)
    structure_to_canonical = {v: k for k, v in mapping.items()}
    if len(structure_to_canonical) != len(mapping):
        raise AmbiguousMapping(
            "The alignment maps more than one canonical residue to the same structure residue."
        )

    residue = structure.residues[structure_index]
    if residue.one_letter != canonical_residue:
        raise PositionUnmapped(
            "The aligned structure residue does not match the canonical wild-type residue.",
            details={
                "position": target_position,
                "canonical_residue": canonical_residue,
                "structure_residue": residue.one_letter,
                "structure_residue_id": residue.residue_id,
            },
        )
    if residue.ca is None:
        raise PositionUnmapped(
            "The aligned structure residue has no CA atom, so structural context cannot be computed.",
            details={"position": target_position, "structure_residue_id": residue.residue_id},
        )

    warnings: list[str] = []
    if total > MAX_ENUMERATED_ALIGNMENTS:
        warnings.append(
            f"Alignment has {total} optimal solutions; the requested column was consistent in the first "
            f"{MAX_ENUMERATED_ALIGNMENTS}. Ambiguity elsewhere cannot be excluded."
        )
    if coverage < 0.9:
        warnings.append(f"Only {coverage:.1%} of canonical residues align to the selected structure chain.")
    if identities / max(len(aligned_pairs), 1) < 0.9:
        warnings.append(
            "Aligned residue identity is below 90%; verify that the structure corresponds to this "
            "UniProt entry."
        )

    return ResidueMapping(
        canonical_position=target_position,
        canonical_residue=canonical_residue,
        structure_index=structure_index,
        structure_chain=structure.chain_id,
        structure_residue_id=residue.residue_id,
        structure_sequence_id=residue.sequence_id,
        insertion_code=residue.insertion_code,
        residue_name=residue.resname,
        residue_three_letter=residue.resname,
        mapping_status="mapped",
        canonical_to_structure=mapping,
        structure_to_canonical=structure_to_canonical,
        alignment={
            "method": "global pairwise alignment (Bio.Align.PairwiseAligner)",
            "match_score": 2.0,
            "mismatch_score": -1.0,
            "gap_open_score": -10.0,
            "gap_extend_score": -0.5,
            "canonical_length": len(canonical_sequence),
            "structure_length": len(observed),
            "aligned_columns": len(aligned_pairs),
            "identities": identities,
            "mismatches": mismatches,
            "canonical_gap_columns": canonical_gap_columns,
            "structure_gap_columns": structure_gap_columns,
            "coverage": round(coverage, 4),
            "optimal_alignments_reported": total,
        },
        warnings=tuple(warnings),
    )
