"""Exact unit algebra for recipe quantities.

Every quantity in this package is a :class:`fractions.Fraction`. Floating point
is not used anywhere in the quantity path, because the arithmetic a cook cares
about is exact: doubling 2/3 cup is 4/3 cup, and three thirds of a cup must come
back as one cup rather than 0.9999999999.

Unit families are volume (base millilitre), mass (base gram) and count (base
each). Conversion inside a family is a multiplication. Conversion between volume
and mass requires a density for the specific ingredient, and the absence of one
is an error rather than a default: treating a cup of flour as a cup of water is
the single most common way a scaled recipe is ruined.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

__all__ = [
    "Unit",
    "UnitError",
    "DensityError",
    "UNITS",
    "lookup",
    "convert",
    "to_base",
    "from_base",
    "density_for",
]


class UnitError(ValueError):
    """Raised when a conversion is not defined."""


class DensityError(UnitError):
    """Raised when a volume/mass conversion needs a density we do not have."""


@dataclass(frozen=True)
class Unit:
    """A named unit, with its factor to the base unit of its family."""

    name: str
    family: str
    factor: Fraction
    approximate: bool = False

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


def _f(text: str) -> Fraction:
    return Fraction(text)


# US customary volumes. teaspoon 1/6 fl oz, tablespoon 1/2 fl oz, cup 8 fl oz,
# all defined from the US fluid ounce of 29.5735295625 ml.
_TSP = _f("4.92892159375")

_VOLUME: tuple[tuple[str, Fraction, tuple[str, ...]], ...] = (
    ("ml", _f("1"), ("milliliter", "millilitre")),
    ("dl", _f("100"), ("deciliter", "decilitre")),
    ("l", _f("1000"), ("liter", "litre")),
    ("tsp", _TSP, ("teaspoon",)),
    ("tbsp", _f("14.78676478125"), ("tablespoon",)),
    ("cup", _f("236.5882365"), ("cups",)),
    ("fl oz", _f("29.5735295625"), ("fluid ounce", "floz")),
    ("pint", _f("473.176473"), ()),
    ("quart", _f("946.352946"), ()),
    ("gallon", _f("3785.411784"), ()),
    ("dash", _TSP / 8, ()),
    ("pinch", _TSP / 16, ()),
)

_MASS: tuple[tuple[str, Fraction, tuple[str, ...]], ...] = (
    ("mg", _f("0.001"), ("milligram",)),
    ("g", _f("1"), ("gram", "gr")),
    ("kg", _f("1000"), ("kilogram",)),
    ("oz", _f("28.349523125"), ("ounce",)),
    ("lb", _f("453.59237"), ("pound",)),
    # A US butter stick is 1/2 cup by volume and 113.4 g by weight.
    ("stick", _f("113.4"), ("sticks",)),
)

_COUNT: tuple[tuple[str, Fraction, tuple[str, ...]], ...] = (
    ("each", _f("1"), ("whole", "unit", "item")),
    ("clove", _f("1"), ("cloves",)),
    ("can", _f("1"), ("cans",)),
    ("jar", _f("1"), ("jars",)),
    ("slice", _f("1"), ("slices",)),
    ("piece", _f("1"), ("pieces",)),
    ("bunch", _f("1"), ("bunches",)),
    ("sprig", _f("1"), ("sprigs",)),
    ("stalk", _f("1"), ("stalks",)),
    ("head", _f("1"), ("heads",)),
    ("fillet", _f("1"), ("fillets",)),
)

APPROXIMATE_UNITS = frozenset({"dash", "pinch"})


def _build_registry() -> dict[str, Unit]:
    registry: dict[str, Unit] = {}
    for family, table in (("volume", _VOLUME), ("mass", _MASS), ("count", _COUNT)):
        for name, factor, aliases in table:
            unit = Unit(name=name, family=family, factor=factor, approximate=name in APPROXIMATE_UNITS)
            registry[name] = unit
            for alias in aliases:
                registry[alias] = unit
    return registry


UNITS: dict[str, Unit] = _build_registry()


def lookup(token: str) -> Unit | None:
    """Resolve a unit token, tolerating a trailing period and a plural.

    Returns ``None`` when the token is not a unit, which the parser reads as
    "this line has no unit" rather than as an error: many ingredients are
    counted ("2 eggs") and some are vague ("salt to taste").
    """

    cleaned = token.strip().lower().rstrip(".")
    if not cleaned:
        return None
    if cleaned in UNITS:
        return UNITS[cleaned]
    if cleaned.endswith("es") and cleaned[:-2] in UNITS:
        return UNITS[cleaned[:-2]]
    if cleaned.endswith("s") and cleaned[:-1] in UNITS:
        return UNITS[cleaned[:-1]]
    return None


# --------------------------------------------------------------------------- #
# Densities
# --------------------------------------------------------------------------- #

# Grams per millilitre. Values are the ones a cook can verify against a kitchen
# scale, rounded to three decimals; each is a documented approximation of a
# physical ingredient, not a constant of nature, which is why the tool prints the
# density it used rather than treating the answer as exact.
_DENSITY_TABLE: tuple[tuple[str, Fraction], ...] = (
    ("all-purpose flour", _f("0.53")),
    ("bread flour", _f("0.55")),
    ("whole wheat flour", _f("0.53")),
    ("almond flour", _f("0.4")),
    ("cake flour", _f("0.48")),
    ("powdered sugar", _f("0.51")),
    ("brown sugar", _f("0.93")),
    ("granulated sugar", _f("0.845")),
    ("cornstarch", _f("0.54")),
    ("cocoa", _f("0.42")),
    ("baking powder", _f("0.9")),
    ("baking soda", _f("0.95")),
    ("peanut butter", _f("1.09")),
    ("sour cream", _f("1.02")),
    ("maple syrup", _f("1.33")),
    ("olive oil", _f("0.918")),
    ("soy sauce", _f("1.16")),
    ("buttermilk", _f("1.03")),
    ("yogurt", _f("1.03")),
    ("butter", _f("0.9593")),
    ("honey", _f("1.42")),
    ("cream", _f("1.01")),
    ("milk", _f("1.03")),
    ("water", _f("1.0")),
    ("stock", _f("1.0")),
    ("broth", _f("1.0")),
    ("wine", _f("0.99")),
    ("vinegar", _f("1.01")),
    ("oil", _f("0.918")),
    ("flour", _f("0.53")),
    ("sugar", _f("0.845")),
    ("salt", _f("1.217")),
    ("rice", _f("0.85")),
    ("oats", _f("0.41")),
    ("yeast", _f("0.6")),
)


def density_for(ingredient: str) -> tuple[Fraction | None, str | None]:
    """Return ``(grams_per_ml, matched_key)`` for an ingredient name.

    The longest matching key wins, so "brown sugar" beats "sugar" and
    "all-purpose flour" beats "flour". A name with no match returns ``(None,
    None)`` and the caller must decide whether that is an error.
    """

    lowered = f" {ingredient.lower()} "
    best: tuple[int, Fraction, str] | None = None
    for key, value in _DENSITY_TABLE:
        if f" {key} " in lowered:
            if best is None or len(key) > best[0]:
                best = (len(key), value, key)
    if best is None:
        return None, None
    return best[1], best[2]


# --------------------------------------------------------------------------- #
# Conversion
# --------------------------------------------------------------------------- #


def to_base(quantity: Fraction, unit: Unit) -> Fraction:
    """Convert ``quantity`` of ``unit`` into the base unit of its family."""

    return quantity * unit.factor


def from_base(base_quantity: Fraction, unit: Unit) -> Fraction:
    """Convert a base-unit quantity into ``unit``."""

    return base_quantity / unit.factor


def convert(
    quantity: Fraction,
    source: Unit,
    target: Unit,
    density: Fraction | None = None,
) -> Fraction:
    """Convert a quantity between units.

    Same-family conversion is always defined. Volume to mass (and back) needs
    ``density`` in grams per millilitre and raises :class:`DensityError` without
    it. Counts convert only to counts.
    """

    if source.family == target.family:
        return from_base(to_base(quantity, source), target)

    if {source.family, target.family} == {"volume", "mass"}:
        if density is None:
            raise DensityError(
                f"cannot convert {source.name} to {target.name} without a density; "
                "name the ingredient so one can be looked up, or pass --density"
            )
        if source.family == "volume":
            grams = to_base(quantity, source) * density
            return from_base(grams, target)
        millilitres = to_base(quantity, source) / density
        return from_base(millilitres, target)

    raise UnitError(f"cannot convert {source.family} to {target.family}")
