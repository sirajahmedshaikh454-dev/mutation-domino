from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.errors import InvalidAccession, InvalidVariant, VariantWtMismatch

VARIANT_RE = re.compile(r"^([ACDEFGHIKLMNPQRSTVWY])(\d+)([ACDEFGHIKLMNPQRSTVWY])$")
ACCESSION_RE = re.compile(r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$")


@dataclass(frozen=True)
class Variant:
    input: str
    wt: str
    position: int
    mutant: str

    @property
    def normalized(self) -> str:
        return f"{self.wt}{self.position}{self.mutant}"


def normalize_accession(raw: str) -> str:
    accession = (raw or "").strip().upper()
    if not accession:
        raise InvalidAccession("No UniProt accession was provided.")
    if "-" in accession:
        raise InvalidAccession(
            "Isoform accessions are not supported in the MVP. Enter the canonical UniProt accession.",
            details={"input": accession},
        )
    if not ACCESSION_RE.fullmatch(accession):
        raise InvalidAccession(
            "That does not look like a canonical UniProt accession (e.g. P69905 or A0A123B4C5).",
            details={"input": accession},
        )
    return accession


def parse_variant(raw: str, canonical_sequence: str) -> Variant:
    text = (raw or "").strip().upper()
    if not text:
        raise InvalidVariant("Enter a missense substitution such as A123V.")
    match = VARIANT_RE.fullmatch(text)
    if not match:
        raise InvalidVariant(
            "Invalid substitution syntax. Use one-letter wild-type, a 1-based position, and mutant "
            "letter, e.g. A123V.",
            details={"input": raw},
        )
    wt, position_text, mutant = match.groups()
    position = int(position_text)
    if position < 1:
        raise InvalidVariant(
            "Position must be a positive 1-based residue number.", details={"position": position}
        )
    sequence_length = len(canonical_sequence)
    if position > sequence_length:
        raise InvalidVariant(
            f"Position {position} is outside the canonical sequence (length {sequence_length}).",
            details={"position": position, "sequence_length": sequence_length},
        )
    canonical_wt = canonical_sequence[position - 1]
    if canonical_wt != wt:
        raise VariantWtMismatch(
            f"Wild-type letter {wt} does not match canonical residue {canonical_wt} at position {position}.",
            details={"position": position, "expected_wt": canonical_wt, "provided_wt": wt},
        )
    if wt == mutant:
        raise InvalidVariant(
            f"{wt}{position}{mutant} is an identity substitution; the mutant letter must differ.",
            details={"position": position},
        )
    return Variant(input=raw, wt=wt, position=position, mutant=mutant)
