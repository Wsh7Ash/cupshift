"""Scaling, rounding, ascent and the flags that keep the output honest."""

from __future__ import annotations

from fractions import Fraction as F

import pytest

from cupshift.parse import parse_recipe
from cupshift.scale import ScaleError, format_quantity, scale_recipe


def recipe(*lines: str, servings: str | None = "4"):
    header = "title: Test\n" + (f"servings: {servings}\n" if servings else "")
    body = "\n".join(lines)
    return parse_recipe(f"{header}\n## ingredients\n{body}\n")


def only(scaled):
    assert len(scaled.items) == 1
    return scaled.items[0]


def test_doubling_is_exact():
    item = only(scale_recipe(recipe("2 cups flour"), factor=F(2)))
    assert (item.quantity_text, item.unit_text) == ("4", "cups")


def test_servings_target_sets_the_factor():
    scaled = scale_recipe(recipe("1 cup milk", servings="4"), target_servings=F(6))
    assert scaled.factor == F(3, 2)
    assert only(scaled).quantity_text == "1 1/2"


def test_format_quantity_renders_mixed_numbers():
    assert format_quantity(F(3, 2)) == "1 1/2"
    assert format_quantity(F(1, 4)) == "1/4"
    assert format_quantity(F(2)) == "2"


def test_three_teaspoons_ascend_to_a_tablespoon():
    item = only(scale_recipe(recipe("1 tsp salt"), factor=F(3)))
    assert (item.quantity_text, item.unit_text) == ("1", "tbsp")


def test_four_tablespoons_ascend_to_a_quarter_cup():
    item = only(scale_recipe(recipe("1 tbsp olive oil"), factor=F(4)))
    assert (item.quantity_text, item.unit_text) == ("1/4", "cup")


def test_thirds_are_preserved_when_doubled():
    item = only(scale_recipe(recipe("2/3 cup milk"), factor=F(2)))
    assert item.quantity_text == "1 1/3"


def test_mass_rounds_in_five_gram_steps():
    item = only(scale_recipe(recipe("100 g butter"), factor=F(3, 2)))
    assert (item.quantity_text, item.unit_text) == ("150", "g")


def test_kilogram_ascent():
    item = only(scale_recipe(recipe("800 g flour"), factor=F(2)))
    assert (item.quantity_text, item.unit_text) == ("1 3/5", "kg")


def test_a_fractional_egg_is_flagged():
    item = only(scale_recipe(recipe("1 egg"), factor=F(3, 2)))
    assert item.quantity_text == "1 1/2"
    assert any("fractional egg" in flag for flag in item.flags)


def test_leavening_is_flagged_as_non_linear():
    item = only(scale_recipe(recipe("1 tsp baking powder"), factor=F(2)))
    assert any("leavening" in flag for flag in item.flags)


def test_seasoning_is_flagged_for_tasting():
    item = only(scale_recipe(recipe("1 tsp salt"), factor=F(2)))
    assert any("season to taste" in flag for flag in item.flags)


def test_unscalable_rows_survive_unchanged():
    item = only(scale_recipe(recipe("salt to taste"), factor=F(3)))
    assert item.unscalable
    assert item.quantity_text == "as written"
    assert item.unit_text is None


def test_metric_mode_converts_volume_to_rounded_millilitres():
    item = only(scale_recipe(recipe("1 cup milk"), factor=F(1), metric=True))
    assert (item.quantity_text, item.unit_text) == ("235", "ml")


def test_metric_mode_keeps_a_small_volume_measurable():
    item = only(scale_recipe(recipe("1/2 tsp baking soda"), factor=F(1), metric=True))
    assert (item.quantity_text, item.unit_text) == ("2 1/2", "ml")


def test_plural_labels_only_for_units_that_have_them():
    cups = only(scale_recipe(recipe("1 cup milk"), factor=F(2)))
    spoons = only(scale_recipe(recipe("1 tsp salt"), factor=F(6)))
    assert cups.unit_text == "cups"
    assert spoons.unit_text == "tbsp"


def test_metric_mode_converts_mass_to_grams():
    item = only(scale_recipe(recipe("1 lb butter"), factor=F(1), metric=True))
    assert item.unit_text == "g"
    assert item.quantity_text == "455"


def test_ranges_keep_their_unit_and_their_shape():
    item = only(scale_recipe(recipe("2-3 tbsp olive oil"), factor=F(2)))
    assert item.quantity_text == "4-6"
    assert item.unit_text == "tbsp"


def test_grams_are_reported_for_a_known_density():
    item = only(scale_recipe(recipe("2 cups all-purpose flour"), factor=F(2)))
    # 4 cups at 0.53 g/ml is 501.57 g, rounded to the same 5 g step the
    # converter uses.
    assert item.grams == "500 g"


def test_grams_are_absent_when_the_density_is_unknown():
    item = only(scale_recipe(recipe("1 cup unobtainium"), factor=F(2)))
    assert item.grams is None


def test_a_negative_factor_is_rejected():
    with pytest.raises(ScaleError):
        scale_recipe(recipe("1 cup milk"), factor=F(-1))


def test_a_target_without_declared_servings_is_rejected():
    with pytest.raises(ScaleError):
        scale_recipe(recipe("1 cup milk", servings=None), target_servings=F(6))


def test_neither_factor_nor_target_is_rejected():
    with pytest.raises(ScaleError):
        scale_recipe(recipe("1 cup milk"))
