from __future__ import annotations

import pytest

from app.domain.errors import InvalidAccession, InvalidVariant, VariantWtMismatch
from app.domain.variant import normalize_accession, parse_variant

SEQUENCE = (
    "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSD"
    "LHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR"
)


def test_accepts_valid_substitution() -> None:
    variant = parse_variant("n10v", SEQUENCE)
    assert variant.normalized == "N10V"
    assert variant.wt == "N"
    assert variant.position == 10
    assert variant.mutant == "V"


@pytest.mark.parametrize("raw", ["", "10V", "AV", "A10", "A10VX", "n10v", "A0V", "A-1V", "A10*"])
def test_rejects_malformed_syntax(raw: str) -> None:
    if raw == "n10v":
        assert parse_variant(raw, SEQUENCE).normalized == "N10V"
        return
    with pytest.raises(InvalidVariant):
        parse_variant(raw, SEQUENCE)


def test_rejects_out_of_range() -> None:
    with pytest.raises(InvalidVariant, match="outside"):
        parse_variant("N999V", SEQUENCE)


def test_rejects_wt_mismatch() -> None:
    with pytest.raises(VariantWtMismatch) as excinfo:
        parse_variant("K10V", SEQUENCE)
    assert excinfo.value.details["expected_wt"] == "N"


def test_rejects_identity() -> None:
    with pytest.raises(InvalidVariant, match="identity"):
        parse_variant("N10N", SEQUENCE)


def test_rejects_noncanonical_letter() -> None:
    with pytest.raises(InvalidVariant):
        parse_variant("B10V", SEQUENCE)


@pytest.mark.parametrize(
    "raw,expected", [("p69905", "P69905"), ("  P69905 ", "P69905"), ("A0A123B4C5", "A0A123B4C5")]
)
def test_accession_normalization(raw: str, expected: str) -> None:
    assert normalize_accession(raw) == expected


@pytest.mark.parametrize("raw", ["", "P6990", "P69905-2", "not-an-accession", "12345"])
def test_accession_rejection(raw: str) -> None:
    with pytest.raises(InvalidAccession):
        normalize_accession(raw)
