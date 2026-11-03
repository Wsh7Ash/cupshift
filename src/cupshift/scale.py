"""Scaling, rounding and the honest flags.

The rules here encode cooking judgement that is easy to state and hard to
remember:

* volumes round to eighths, quarters, thirds and halves, never to decimals;
* masses round in gram steps that a kitchen scale can display;
* small units ascend when they get large (3 tsp -> 1 tbsp, 4 tbsp -> 1/4 cup);
* eggs refuse to be divided neatly, so a fractional egg becomes grams;
* leavening and seasoning are flagged, because they do not scale linearly in
  practice even though the arithmetic does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .parse import Ingredient, Recipe
from .units import UNITS, Unit, density_for, to_base

__all__ = [
    "ScaleError",
    "ScaledItem",
    "ScaledRecipe",
    "format_quantity",
    "scale_recipe",
    "round_value",
    "ascend",
]


class ScaleError(ValueError):
    """Raised when a scaling request is not answerable."""


VOLUME_FRACTIONS: tuple[Fraction, ...] = (
    Fraction(0),
    Fraction(1, 8),
    Fraction(1, 4),
    Fraction(1, 3),
    Fraction(1, 2),
    Fraction(2, 3),
    Fraction(3, 4),
    Fraction(1),
)

#: unit -> (next unit, threshold in the current unit)
ASCENT: dict[str, tuple[str, Fraction]] = {
    "tsp": ("tbsp", Fraction(3)),
    "tbsp": ("cup", Fraction(4)),
    "g": ("kg", Fraction(1000)),
    "ml": ("l", Fraction(1000)),
    "oz": ("lb", Fraction(16)),
}

#: Units whose printed label changes with a plural quantity. Abbreviations such
#: as "tbsp" and "g" do not, which is why this is an explicit table rather than
#: a rule that appends an "s".
PLURAL_UNITS: dict[str, str] = {
    "cup": "cups",
    "clove": "cloves",
    "can": "cans",
    "jar": "jars",
    "slice": "slices",
    "piece": "pieces",
    "bunch": "bunches",
    "sprig": "sprigs",
    "stalk": "stalks",
    "head": "heads",
    "fillet": "fillets",
    "stick": "sticks",
    "pint": "pints",
    "quart": "quarts",
    "gallon": "gallons",
    "pinch": "pinches",
    "dash": "dashes",
}


def unit_label(value: Fraction | None, unit: Unit | None) -> str | None:
    """Human label for a unit at a given quantity (``2 cups``, but ``1 cup``)."""

    if unit is None:
        return None
    # English keeps a fraction singular: "1/4 cup", not "1/4 cups". Only a
    # quantity above one takes the plural.
    if value is not None and value > 1 and unit.name in PLURAL_UNITS:
        return PLURAL_UNITS[unit.name]
    return unit.name


LEAVENING = ("baking powder", "baking soda", "bicarbonate", "yeast", "self-raising", "self-rising")
SEASONING = ("salt", "pepper", "spice", "chili", "chilli", "paprika", "cumin", "cinnamon", "nutmeg", "cayenne")
EGG = "egg"


def format_quantity(value: Fraction) -> str:
    """Render a rational quantity as an ASCII cooking fraction."""

    if value.denominator == 1:
        return str(value.numerator)
    whole, remainder = divmod(value.numerator, value.denominator)
    if whole:
        return f"{whole} {remainder}/{value.denominator}"
    return f"{value.numerator}/{value.denominator}"


def _round_half_up(value: Fraction) -> int:
    """Round a non-negative rational to the nearest integer, halves upward."""

    return int(value + Fraction(1, 2))


def _round_volume(value: Fraction) -> Fraction:
    whole = Fraction(int(value))
    fraction = value - whole
    best = min(VOLUME_FRACTIONS, key=lambda candidate: abs(candidate - fraction))
    if abs(best - fraction) <= Fraction(1, 50):
        return whole + best
    return Fraction(_round_half_up(value * 8), 8)


def _round_mass(value: Fraction, unit: Unit) -> Fraction:
    grams = to_base(value, unit)
    if grams < 10:
        step = Fraction(1, 2)
    elif grams < 100:
        step = Fraction(1)
    elif grams < 1000:
        step = Fraction(5)
    else:
        step = Fraction(10)
    rounded_grams = Fraction(_round_half_up(grams / step)) * step
    return rounded_grams / unit.factor


def _round_metric_volume(value: Fraction, unit: Unit) -> Fraction:
    millilitres = to_base(value, unit)
    # A coarse step erases small quantities: a half teaspoon is 2.46 ml, and
    # rounding it with a 5 ml step produced "0 ml" on a real recipe card. Below
    # ten millilitres the step is half a millilitre, which is still measurable.
    if millilitres < 10:
        step = Fraction(1, 2)
    elif millilitres < 1000:
        step = Fraction(5)
    else:
        step = Fraction(50)
    return Fraction(_round_half_up(millilitres / step)) * step / unit.factor


def _round_count(value: Fraction) -> Fraction:
    if value >= 1:
        return Fraction(_round_half_up(value * 2), 2)
    return Fraction(_round_half_up(value * 4), 4)


def round_value(value: Fraction, unit: Unit | None) -> Fraction:
    """Round a quantity to something a cook can measure with that unit."""

    if unit is None:
        return _round_count(value)
    if unit.family == "count":
        return _round_count(value)
    if unit.name in {"ml", "dl", "l"}:
        return _round_metric_volume(value, unit)
    if unit.family == "mass":
        return _round_mass(value, unit)
    return _round_volume(value)


def ascend(value: Fraction, unit: Unit | None) -> tuple[Fraction, Unit | None]:
    """Move up to a larger unit when the quantity has outgrown the small one."""

    current_unit = unit
    current = value
    for _ in range(3):
        if current_unit is None:
            break
        step = ASCENT.get(current_unit.name)
        if step is None:
            break
        target_name, threshold = step
        if current < threshold:
            break
        target = UNITS[target_name]
        current = current * current_unit.factor / target.factor
        current_unit = target
    return current, current_unit


def _to_metric(value: Fraction, unit: Unit | None) -> tuple[Fraction, Unit | None]:
    if unit is None:
        return value, unit
    if unit.family == "volume":
        millilitres = to_base(value, unit)
        if millilitres >= 1000:
            return millilitres / UNITS["l"].factor, UNITS["l"]
        return millilitres, UNITS["ml"]
    if unit.family == "mass":
        grams = to_base(value, unit)
        if grams >= 1000:
            return grams / UNITS["kg"].factor, UNITS["kg"]
        return grams, UNITS["g"]
    return value, unit


@dataclass
class ScaledItem:
    name: str
    quantity: Fraction | None
    quantity_text: str
    unit_text: str | None
    grams: str | None = None
    note: str | None = None
    package: str | None = None
    flags: list[str] = field(default_factory=list)
    unscalable: bool = False
    original: str | None = None

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity_text,
            "unit": self.unit_text,
            "grams": self.grams,
            "note": self.note,
            "package": self.package,
            "flags": self.flags,
            "unscalable": self.unscalable,
            "original": self.original,
        }


@dataclass
class ScaledRecipe:
    title: str
    factor: Fraction
    source_servings: Fraction | None
    target_servings: Fraction | None
    items: list[ScaledItem]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "factor": format_quantity(self.factor),
            "factor_value": float(self.factor),
            "source_servings": str(self.source_servings) if self.source_servings else None,
            "target_servings": str(self.target_servings) if self.target_servings else None,
            "items": [item.as_dict() for item in self.items],
            "notes": self.notes,
        }


def _item_flags(name: str, unit: Unit | None, value: Fraction | None) -> list[str]:
    lowered = name.lower()
    flags: list[str] = []
    if any(word in lowered for word in LEAVENING):
        flags.append("leavening does not scale linearly; check the rise and texture")
    if any(word in lowered for word in SEASONING):
        flags.append("season to taste after scaling rather than trusting the arithmetic")
    if EGG in lowered and (unit is None or unit.family == "count") and value is not None:
        if value.denominator != 1:
            flags.append("fractional egg: beat whole eggs and weigh out the part you need")
    return flags


def _scale_item(ingredient: Ingredient, factor: Fraction, metric: bool) -> ScaledItem:
    if ingredient.unscalable or ingredient.quantity is None:
        return ScaledItem(
            name=ingredient.name,
            quantity=None,
            quantity_text="as written",
            unit_text=None,
            note=ingredient.note,
            package=ingredient.package,
            flags=[ingredient.reason or "not scaled"],
            unscalable=True,
            original=ingredient.raw,
        )

    unit = ingredient.unit
    value = ingredient.quantity * factor

    # A range keeps the shape of the original line: the high end is scaled by the
    # same ratio as the low end, so "2-3 tbsp" stays a range instead of collapsing
    # to a single number.
    ratio = (
        ingredient.quantity_high / ingredient.quantity
        if ingredient.quantity_high is not None and ingredient.quantity
        else None
    )

    if metric:
        value, unit = _to_metric(value, unit)

    # A range keeps the unit it was written in: ascending "2-3 tbsp" to cups
    # would produce a range nobody wants to measure.
    if ratio is None:
        value, unit = ascend(value, unit)

    low = round_value(value, unit)
    high = round_value(value * ratio, unit) if ratio is not None else None

    quantity_text = format_quantity(low) if high is None else f"{format_quantity(low)}-{format_quantity(high)}"

    grams_value: Fraction | None = None
    if unit is not None and unit.family == "mass":
        grams_value = to_base(low, unit)
    elif unit is not None and unit.family == "volume":
        density, _key = density_for(ingredient.name)
        if density is not None:
            grams_value = to_base(low, unit) * density

    # The grams annotation uses the same rounding as ``convert --to g``, so the
    # card and the converter never disagree about the same ingredient.
    grams = (
        f"{_round_half_up(round_value(grams_value, UNITS['g']))} g"
        if grams_value is not None
        else None
    )

    flags = _item_flags(ingredient.name, unit, low)

    return ScaledItem(
        name=ingredient.name,
        quantity=low,
        quantity_text=quantity_text,
        unit_text=unit_label(high if high is not None else low, unit),
        grams=grams,
        note=ingredient.note,
        package=ingredient.package,
        flags=flags,
        original=ingredient.raw,
    )


def scale_recipe(
    recipe: Recipe,
    factor: Fraction | None = None,
    target_servings: Fraction | None = None,
    metric: bool = False,
) -> ScaledRecipe:
    """Scale a recipe by a factor or to a target number of servings."""

    if factor is None:
        if target_servings is None:
            raise ScaleError("give either a factor or a target number of servings")
        if recipe.servings is None:
            raise ScaleError("the recipe does not declare servings, so a target cannot be derived")
        factor = target_servings / recipe.servings

    if factor <= 0:
        raise ScaleError("the scaling factor must be positive")

    items = [_scale_item(ingredient, factor, metric) for ingredient in recipe.ingredients]

    notes: list[str] = []
    if recipe.servings is not None and target_servings is not None:
        notes.append(
            f"servings {format_quantity(recipe.servings)} -> {format_quantity(target_servings)}"
        )
    notes.append(f"factor {format_quantity(factor)}x")
    if any(item.unscalable for item in items):
        notes.append("rows marked 'as written' keep the original wording because the amount was open")

    return ScaledRecipe(
        title=recipe.title,
        factor=factor,
        source_servings=recipe.servings,
        target_servings=target_servings,
        items=items,
        notes=notes,
    )
