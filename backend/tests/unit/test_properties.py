from __future__ import annotations

import pytest

from app.domain.properties import (
    AMINO_ACIDS,
    ONE_TO_THREE,
    THREE_TO_ONE,
    property_deltas,
    residue_properties,
)


def test_tables_are_consistent() -> None:
    assert set(AMINO_ACIDS) == set(THREE_TO_ONE.values())
    assert set(ONE_TO_THREE) == set(THREE_TO_ONE.values())
    assert set(ONE_TO_THREE.values()) == set(THREE_TO_ONE)
    for letter in AMINO_ACIDS:
        props = residue_properties(letter)
        assert props.one_letter == letter
        assert ONE_TO_THREE[letter] == props.three_letter


def test_property_deltas_values() -> None:
    result = property_deltas("A", "V")
    assert result["wild_type"]["hydropathy"] == 1.8
    assert result["mutant"]["hydropathy"] == 4.2
    assert result["deltas"]["hydropathy"] == pytest.approx(2.4)
    assert result["deltas"]["category_changed"] is False
    assert result["table"]["version"] == "1.0.0"


def test_charge_change_is_reported() -> None:
    result = property_deltas("K", "E")
    assert result["wild_type"]["charge_class"] == "positive"
    assert result["mutant"]["charge_class"] == "negative"
    assert result["deltas"]["charge_class_changed"] is True


def test_unknown_residue_rejected() -> None:
    with pytest.raises(ValueError):
        residue_properties("B")
