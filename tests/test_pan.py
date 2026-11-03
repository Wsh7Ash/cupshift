"""Pan geometry: areas, exact round-to-round ratios and the warnings."""

from __future__ import annotations

from fractions import Fraction as F

import pytest

from cupshift.pan import PanError, pan_factor, parse_pan


def test_round_tin_parsed_from_inches():
    pan = parse_pan("9in round")
    assert pan.shape == "round"
    assert pan.width_cm == F("22.86")


def test_square_tin_parsed_with_a_shared_unit():
    pan = parse_pan("8x8in square")
    assert pan.shape == "square"
    assert (pan.width_cm, pan.length_cm) == (F("20.32"), F("20.32"))


def test_rectangular_tin_with_a_space():
    pan = parse_pan("9x13 in")
    assert pan.shape == "rect"
    assert pan.length_cm == F("33.02")


def test_centimetres():
    assert parse_pan("20cm round").width_cm == F(20)


def test_millimetres_are_converted():
    assert parse_pan("200mm round").width_cm == F(20)


def test_inch_marks_are_accepted():
    assert parse_pan('9" round').width_cm == F("22.86")


def test_nine_inch_to_eight_inch_round_is_exactly_sixty_four_over_eighty_one():
    factor, _ = pan_factor(parse_pan("9in round"), parse_pan("8in round"))
    assert factor == F(64, 81)


def test_round_and_square_tins_of_similar_area_are_nearly_one_to_one():
    factor, _ = pan_factor(parse_pan("9in round"), parse_pan("8x8in square"))
    assert F(99, 100) < factor < F(102, 100)


def test_depth_makes_the_factor_a_volume_ratio():
    factor, notes = pan_factor(parse_pan("9in round"), parse_pan("9in round"), F(2), F(3))
    assert factor == F(3, 2)
    assert any("volume" in note for note in notes)


def test_a_much_larger_tin_produces_a_warning():
    _, notes = pan_factor(parse_pan("9in round"), parse_pan("9x13 in"))
    assert any("much larger" in note for note in notes)


def test_a_much_smaller_tin_produces_a_warning():
    _, notes = pan_factor(parse_pan("9x13 in"), parse_pan("6in round"))
    assert any("much smaller" in note for note in notes)


def test_unreadable_pan_is_rejected():
    with pytest.raises(PanError):
        parse_pan("a big one")


def test_zero_dimension_is_rejected():
    with pytest.raises(PanError):
        parse_pan("0in round")
