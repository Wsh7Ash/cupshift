"""Parsing of ingredient lines and plain-text recipe files.

The recipe format is deliberately boring so that a cook can keep recipes in any
editor and so that the parser can be tested exhaustively:

```text
title: Buttermilk Pancakes
servings: 8

## ingredients
2 cups all-purpose flour
1 1/2 tsp baking powder
2 large eggs
salt to taste
1 (14 oz) can tomatoes

## method
Whisk the dry ingredients.
```

Anything outside the two section markers is either a `key: value` header or a
comment. Ingredient lines that cannot be parsed raise with the line number
rather than being silently dropped, because a silently dropped ingredient is a
scaled recipe that is missing an ingredient.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from .units import Unit, lookup

__all__ = [
    "ParseError",
    "Ingredient",
    "Recipe",
    "parse_ingredient",
    "parse_quantity",
    "parse_recipe",
    "parse_recipe_file",
]


class ParseError(ValueError):
    """Raised when a line cannot be understood as an ingredient or a recipe."""


UNICODE_FRACTIONS: dict[str, Fraction] = {
    "\u00bc": Fraction(1, 4),
    "\u00bd": Fraction(1, 2),
    "\u00be": Fraction(3, 4),
    "\u2150": Fraction(1, 7),
    "\u2151": Fraction(1, 9),
    "\u2152": Fraction(1, 10),
    "\u2153": Fraction(1, 3),
    "\u2154": Fraction(2, 3),
    "\u2155": Fraction(1, 5),
    "\u2156": Fraction(2, 5),
    "\u2157": Fraction(3, 5),
    "\u2158": Fraction(4, 5),
    "\u2159": Fraction(1, 6),
    "\u215a": Fraction(5, 6),
    "\u215b": Fraction(1, 8),
    "\u215c": Fraction(3, 8),
    "\u215d": Fraction(5, 8),
    "\u215e": Fraction(7, 8),
}

_UNICODE_CLASS = "".join(re.escape(char) for char in UNICODE_FRACTIONS)

_MIXED = re.compile(r"^(\d+)\s+(\d+)\s*/\s*(\d+)\b")
_FRACTION = re.compile(r"^(\d+)\s*/\s*(\d+)\b")
_UNICODE = re.compile(rf"^(\d+)?\s*([{_UNICODE_CLASS}])")
_RANGE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(?:-|\u2013|\u2014|\bto\b)\s*(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_DECIMAL = re.compile(r"^(\d+(?:\.\d+)?)\b")

_UNSCALABLE_PHRASES: tuple[tuple[str, str], ...] = (
    ("to taste", "seasoned to taste in the original recipe"),
    ("as needed", "the original recipe leaves the amount open"),
    ("as required", "the original recipe leaves the amount open"),
    ("for garnish", "a garnish amount"),
    ("for serving", "a serving amount"),
    ("to serve", "a serving amount"),
    ("for greasing", "a pan-greasing amount"),
    ("for dusting", "a dusting amount"),
)


@dataclass
class Ingredient:
    """One parsed ingredient line."""

    raw: str
    quantity: Fraction | None
    quantity_high: Fraction | None = None
    unit: Unit | None = None
    name: str = ""
    note: str | None = None
    package: str | None = None
    unscalable: bool = False
    reason: str | None = None

    @property
    def is_range(self) -> bool:
        return self.quantity_high is not None


@dataclass
class Recipe:
    title: str
    servings: Fraction | None
    ingredients: list[Ingredient] = field(default_factory=list)
    method: list[str] = field(default_factory=list)
    source: str | None = None


def parse_quantity(text: str) -> tuple[Fraction | None, Fraction | None, str]:
    """Split a leading quantity from ``text``.

    Returns ``(low, high, remainder)``. ``high`` is set only for a range such as
    "2-3" or "1 to 2". A line with no leading number returns ``(None, None,
    text)``, which the ingredient parser treats as a zero-quantity line rather
    than as an error.
    """

    stripped = text.strip()
    if not stripped:
        return None, None, ""

    match = _MIXED.match(stripped)
    if match:
        whole, numerator, denominator = (int(part) for part in match.groups())
        if denominator == 0:
            raise ParseError(f"zero denominator in quantity: {stripped!r}")
        value = Fraction(whole) + Fraction(numerator, denominator)
        return value, None, stripped[match.end() :].strip()

    match = _UNICODE.match(stripped)
    if match:
        whole = int(match.group(1) or 0)
        value = Fraction(whole) + UNICODE_FRACTIONS[match.group(2)]
        return value, None, stripped[match.end() :].strip()

    match = _FRACTION.match(stripped)
    if match:
        numerator, denominator = (int(part) for part in match.groups())
        if denominator == 0:
            raise ParseError(f"zero denominator in quantity: {stripped!r}")
        return Fraction(numerator, denominator), None, stripped[match.end() :].strip()

    match = _RANGE.match(stripped)
    if match:
        low = Fraction(match.group(1))
        high = Fraction(match.group(2))
        if high < low:
            raise ParseError(f"range ends below its start: {stripped!r}")
        return low, high, stripped[match.end() :].strip()

    match = _DECIMAL.match(stripped)
    if match:
        return Fraction(match.group(1)), None, stripped[match.end() :].strip()

    return None, None, stripped


def _take_package(tokens: list[str]) -> tuple[str | None, list[str]]:
    if not tokens or not tokens[0].startswith("("):
        return None, tokens
    joined = " ".join(tokens)
    match = re.match(r"^\(([^)]*)\)", joined)
    if not match:
        return None, tokens
    return match.group(1).strip(), joined[match.end() :].split()


def _take_unit(tokens: list[str]) -> tuple[Unit | None, list[str]]:
    if not tokens:
        return None, tokens
    head = tokens[0].lower()
    if head == "fl" and len(tokens) > 1 and tokens[1].lower().rstrip(".").startswith("oz"):
        return lookup("fl oz"), tokens[2:]
    unit = lookup(tokens[0])
    if unit is None:
        return None, tokens
    return unit, tokens[1:]


def parse_ingredient(line: str) -> Ingredient:
    """Parse one ingredient line into its parts."""

    raw = line.strip()
    if not raw:
        raise ParseError("empty ingredient line")

    working = raw
    unscalable = False
    reason: str | None = None
    lowered = working.lower()
    for phrase, explanation in _UNSCALABLE_PHRASES:
        index = lowered.find(phrase)
        if index != -1:
            unscalable = True
            reason = explanation
            working = (working[:index] + working[index + len(phrase) :]).strip(" ,;")
            lowered = working.lower()
            break

    low, high, rest = parse_quantity(working)

    if low is None and not unscalable:
        match = re.match(r"^(?:a|an)\s+", working, re.IGNORECASE)
        if match:
            following = working[match.end() :].split()
            if following and lookup(following[0]) is not None:
                low = Fraction(1)
                rest = working[match.end() :].strip()

    tokens = rest.split()
    package, tokens = _take_package(tokens)
    unit, tokens = _take_unit(tokens)
    second_package, tokens = _take_package(tokens)
    package = package or second_package

    name = " ".join(tokens).strip(" ,;")
    name = re.sub(r"^of\s+", "", name, flags=re.IGNORECASE)

    note: str | None = None
    if "," in name:
        head, _, tail = name.partition(",")
        head, tail = head.strip(), tail.strip()
        if head and tail:
            name, note = head, tail
        elif head:
            name = head

    if not name:
        raise ParseError(f"ingredient line has no name: {raw!r}")

    if low is None:
        unscalable = True
        reason = reason or "no quantity in the original recipe"

    return Ingredient(
        raw=raw,
        quantity=low,
        quantity_high=high,
        unit=unit,
        name=name,
        note=note,
        package=package,
        unscalable=unscalable,
        reason=reason,
    )


def _parse_servings(value: str) -> Fraction:
    low, high, remainder = parse_quantity(value)
    if low is None:
        raise ParseError(f"servings value is not a number: {value!r}")
    if remainder:
        raise ParseError(f"unexpected text after servings value: {remainder!r}")
    if low <= 0:
        raise ParseError(f"servings must be positive: {value!r}")
    if high is not None:
        return high
    return low


_SECTION_INGREDIENTS = re.compile(r"^#{1,3}\s*ingredients?\b", re.IGNORECASE)
_SECTION_METHOD = re.compile(r"^#{1,3}\s*(method|directions|steps|preparation)\b", re.IGNORECASE)


def parse_recipe(text: str, source: str | None = None) -> Recipe:
    """Parse a recipe document."""

    title = ""
    servings: Fraction | None = None
    ingredients: list[Ingredient] = []
    method: list[str] = []
    section: str | None = None
    saw_ingredients = False

    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        if _SECTION_INGREDIENTS.match(stripped):
            section = "ingredients"
            saw_ingredients = True
            continue
        if _SECTION_METHOD.match(stripped):
            section = "method"
            continue

        if section is None:
            if stripped.startswith("#") and not title:
                title = stripped.lstrip("#").strip()
                continue
            lowered = stripped.lower()
            if lowered.startswith("title:"):
                title = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith(("servings:", "serves:", "yield:")):
                servings = _parse_servings(stripped.split(":", 1)[1].strip())
                continue
            raise ParseError(
                f"line {number}: text before the ingredients section is not a header: {stripped!r}"
            )

        if section == "ingredients":
            if stripped.startswith("#"):
                continue
            try:
                ingredients.append(parse_ingredient(stripped))
            except ParseError as error:
                raise ParseError(f"line {number}: {error}") from error
        else:
            method.append(line.rstrip())

    if not saw_ingredients:
        raise ParseError("recipe has no '## ingredients' section")
    if not ingredients:
        raise ParseError("recipe ingredients section is empty")

    return Recipe(
        title=title or "Untitled recipe",
        servings=servings,
        ingredients=ingredients,
        method=[line for line in method if line.strip()],
        source=source,
    )


def parse_recipe_file(path: str | Path) -> Recipe:
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as error:
        raise ParseError(f"cannot read recipe {target}: {error}") from error
    return parse_recipe(text, source=str(target))
