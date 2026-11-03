"""Ingredient and recipe parsing, including the shapes that must be rejected."""

from __future__ import annotations

from fractions import Fraction as F

import pytest

from cupshift.parse import ParseError, parse_ingredient, parse_quantity, parse_recipe


def test_mixed_number_with_preparation_note():
    ingredient = parse_ingredient("1 1/2 cups all-purpose flour, sifted")
    assert ingredient.quantity == F(3, 2)
    assert ingredient.unit.name == "cup"
    assert ingredient.name == "all-purpose flour"
    assert ingredient.note == "sifted"


def test_unicode_fraction():
    ingredient = parse_ingredient("1\u00bd tsp salt")
    assert ingredient.quantity == F(3, 2)
    assert ingredient.unit.name == "tsp"


def test_leading_unicode_fraction_without_whole_number():
    ingredient = parse_ingredient("\u00be cup milk")
    assert ingredient.quantity == F(3, 4)


def test_plain_fraction():
    assert parse_ingredient("1/2 cup milk").quantity == F(1, 2)


def test_decimal_is_converted_to_an_exact_fraction():
    assert parse_ingredient("0.5 cup milk").quantity == F(1, 2)


def test_range_with_hyphen():
    ingredient = parse_ingredient("2-3 tbsp olive oil")
    assert ingredient.quantity == F(2)
    assert ingredient.quantity_high == F(3)
    assert ingredient.is_range


def test_range_with_the_word_to():
    ingredient = parse_ingredient("1 to 2 cloves garlic")
    assert (ingredient.quantity, ingredient.quantity_high) == (F(1), F(2))
    assert ingredient.unit.name == "clove"


def test_package_size_in_parentheses():
    ingredient = parse_ingredient("1 (14 oz) can chopped tomatoes")
    assert ingredient.quantity == F(1)
    assert ingredient.unit.name == "can"
    assert ingredient.package == "14 oz"
    assert ingredient.name == "chopped tomatoes"


def test_article_before_a_unit_counts_as_one():
    ingredient = parse_ingredient("a pinch of cayenne")
    assert ingredient.quantity == F(1)
    assert ingredient.unit.name == "pinch"
    assert ingredient.name == "cayenne"


def test_to_taste_is_not_scaled():
    ingredient = parse_ingredient("salt to taste")
    assert ingredient.unscalable
    assert ingredient.quantity is None
    assert ingredient.name == "salt"
    assert ingredient.reason


def test_count_line_without_a_unit():
    ingredient = parse_ingredient("3 large eggs")
    assert ingredient.quantity == F(3)
    assert ingredient.unit is None
    assert ingredient.name == "large eggs"


def test_optional_is_a_note_not_an_unscalable_marker():
    ingredient = parse_ingredient("1/4 cup cream, optional")
    assert ingredient.quantity == F(1, 4)
    assert ingredient.note == "optional"
    assert not ingredient.unscalable


def test_missing_name_is_rejected():
    with pytest.raises(ParseError):
        parse_ingredient("2 cups")


def test_zero_denominator_is_rejected():
    with pytest.raises(ParseError):
        parse_ingredient("1/0 cup sugar")


def test_range_ending_below_its_start_is_rejected():
    with pytest.raises(ParseError):
        parse_ingredient("3-2 tbsp oil")


def test_parse_quantity_reports_the_remainder():
    low, high, rest = parse_quantity("2 1/4 cups flour")
    assert (low, high, rest) == (F(9, 4), None, "cups flour")


def test_recipe_parses_headers_and_sections():
    recipe = parse_recipe(
        "title: Test Cake\nservings: 8\n\n## ingredients\n2 cups flour\n\n## method\nMix it.\nBake it.\n"
    )
    assert recipe.title == "Test Cake"
    assert recipe.servings == F(8)
    assert len(recipe.ingredients) == 1
    assert recipe.method == ["Mix it.", "Bake it."]


def test_recipe_without_ingredients_section_is_rejected():
    with pytest.raises(ParseError):
        parse_recipe("title: Empty\nservings: 2\n\n## method\nNothing.\n")


def test_empty_ingredients_section_is_rejected():
    with pytest.raises(ParseError):
        parse_recipe("title: Empty\nservings: 2\n\n## ingredients\n\n## method\nNothing.\n")


def test_ingredient_error_carries_the_line_number():
    with pytest.raises(ParseError) as caught:
        parse_recipe("title: T\nservings: 1\n\n## ingredients\n2 cups\n")
    assert "line 5" in str(caught.value)


def test_text_before_the_first_section_must_be_a_header():
    with pytest.raises(ParseError):
        parse_recipe("just some prose\n\n## ingredients\n1 egg\n")
