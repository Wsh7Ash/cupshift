"""Unit registry and conversion: the arithmetic has to be exact where it matters."""

from __future__ import annotations

from fractions import Fraction as F

import pytest

from cupshift.units import DensityError, UnitError, convert, density_for, lookup


def test_three_teaspoons_are_one_tablespoon_exactly():
    assert convert(F(3), lookup("tsp"), lookup("tbsp")) == F(1)


def test_sixteen_tablespoons_are_one_cup_exactly():
    assert convert(F(16), lookup("tbsp"), lookup("cup")) == F(1)


def test_a_pound_is_sixteen_ounces_exactly():
    assert convert(F(1), lookup("lb"), lookup("oz")) == F(16)


def test_a_kilogram_is_a_thousand_grams():
    assert convert(F(1), lookup("kg"), lookup("g")) == F(1000)


def test_a_cup_is_the_us_customary_volume():
    assert convert(F(1), lookup("cup"), lookup("ml")) == F("236.5882365")


def test_flour_cup_is_about_125_grams():
    density, key = density_for("all-purpose flour")
    assert key == "all-purpose flour"
    grams = convert(F(1), lookup("cup"), lookup("g"), density)
    assert F(124) < grams < F(126)


def test_sugar_cup_is_about_200_grams():
    density, _ = density_for("granulated sugar")
    grams = convert(F(1), lookup("cup"), lookup("g"), density)
    assert F(198) < grams < F(202)


def test_volume_to_mass_without_density_is_an_error():
    with pytest.raises(DensityError):
        convert(F(1), lookup("cup"), lookup("g"))


def test_counts_do_not_convert_to_volume():
    with pytest.raises(UnitError):
        convert(F(1), lookup("each"), lookup("cup"))


def test_lookup_tolerates_plural_and_trailing_period():
    assert lookup("tablespoons.").name == "tbsp"
    assert lookup("cloves").name == "clove"
    assert lookup("bunches").name == "bunch"


def test_lookup_returns_none_for_an_unknown_token():
    assert lookup("smidgen") is None


def test_longest_density_key_wins():
    density, key = density_for("1 cup packed brown sugar")
    assert key == "brown sugar"
    assert density == F("0.93")


def test_density_of_an_unknown_ingredient_is_none():
    assert density_for("unobtainium") == (None, None)


def test_water_round_trips_between_mass_and_volume():
    density, _ = density_for("water")
    assert convert(F(250), lookup("g"), lookup("ml"), density) == F(250)


def test_a_butter_stick_is_mass_and_volume():
    grams = convert(F(1), lookup("stick"), lookup("g"))
    assert grams == F("113.4")
    density, _ = density_for("butter")
    cups = convert(F(1), lookup("stick"), lookup("cup"), density)
    assert F("0.49") < cups < F("0.51")
