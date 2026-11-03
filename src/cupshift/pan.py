"""Pan geometry.

Two tins of different shapes hold different amounts of batter, and the difference
is area (times depth), not diameter. A 9-inch round tin and an 8-inch square tin
are within four percent of each other in area, which surprises most cooks and is
the reason this module exists.

Areas are exact rationals. For the round/round case the factor of pi cancels
exactly, so converting a 9-inch round tin to an 8-inch round tin is the ratio of
the squared radii and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from re import compile as re_compile

__all__ = ["Pan", "PanError", "parse_pan", "pan_factor"]

#: pi to fifteen places as a rational. It cancels in round-to-round ratios; it
#: only affects mixed-shape comparisons, where the printed factor is an
#: approximation and is labelled as one.
PI = Fraction(3141592653589793, 10**15)

_UNIT_TO_CM = {
    "mm": Fraction(1, 10),
    "cm": Fraction(1),
    "in": Fraction(254, 100),
    "inch": Fraction(254, 100),
    "inches": Fraction(254, 100),
    '"': Fraction(254, 100),
}

_UNIT_PATTERN = r"mm|cm|in(?:ch(?:es)?)?|\""

#: Two dimensions first: "9x13in", "8 x 8 in", with the unit allowed on either
#: side and shared when it appears once.
_RECT = re_compile(
    rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT_PATTERN})?\s*[x\u00d7]\s*"
    rf"(?P<value2>\d+(?:\.\d+)?)\s*(?P<unit2>{_UNIT_PATTERN})"
)

_SINGLE = re_compile(rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT_PATTERN})")


class PanError(ValueError):
    """Raised when a pan description cannot be understood."""


@dataclass(frozen=True)
class Pan:
    shape: str  # "round" | "square" | "rect"
    width_cm: Fraction
    length_cm: Fraction
    depth_cm: Fraction | None = None

    @property
    def area_cm2(self) -> Fraction:
        if self.shape == "round":
            radius = self.width_cm / 2
            return PI * radius * radius
        return self.width_cm * self.length_cm

    def volume_cm3(self) -> Fraction:
        return self.area_cm2 * self.depth_cm if self.depth_cm is not None else self.area_cm2


def _to_cm(value: str, unit: str) -> Fraction:
    key = unit.lower()
    if key not in _UNIT_TO_CM:
        raise PanError(f"unknown length unit: {unit!r}")
    return Fraction(value) * _UNIT_TO_CM[key]


def parse_pan(text: str) -> Pan:
    """Parse ``9in round``, ``20cm round``, ``8x8in square`` or ``9x13 in``."""

    cleaned = text.strip().lower()
    if not cleaned:
        raise PanError("no pan description given")

    rectangle = _RECT.search(cleaned)
    if rectangle:
        unit2 = rectangle.group("unit2")
        unit1 = rectangle.group("unit") or unit2
        width = _to_cm(rectangle.group("value"), unit1)
        length = _to_cm(rectangle.group("value2"), unit2)
        if width <= 0 or length <= 0:
            raise PanError("pan dimensions must be positive")
        shape = "square" if width == length else "rect"
    else:
        single = _SINGLE.search(cleaned)
        if not single:
            raise PanError(f"cannot read a dimension from {text!r}; try '9in round' or '9x13in'")
        width = length = _to_cm(single.group("value"), single.group("unit"))
        if width <= 0:
            raise PanError("pan dimensions must be positive")
        shape = "round"

    if "round" in cleaned or "springform" in cleaned:
        shape = "round"

    return Pan(shape=shape, width_cm=width, length_cm=length)


def pan_factor(
    source: Pan,
    target: Pan,
    source_depth_cm: Fraction | None = None,
    target_depth_cm: Fraction | None = None,
) -> tuple[Fraction, list[str]]:
    """Return ``(factor, notes)`` for replacing ``source`` with ``target``.

    Without depths the factor is the area ratio, which assumes the batter fills
    both tins to the same depth. With depths it is the volume ratio.
    """

    if source_depth_cm is not None and target_depth_cm is not None:
        if source_depth_cm <= 0 or target_depth_cm <= 0:
            raise PanError("depths must be positive")
        factor = (target.area_cm2 * target_depth_cm) / (source.area_cm2 * source_depth_cm)
        basis = "volume (area times depth)"
    else:
        factor = target.area_cm2 / source.area_cm2
        basis = "area"

    notes = [f"factor is the {basis} ratio, assuming the same filling depth" if basis == "area" else f"factor is the {basis} ratio"]

    if factor < Fraction(7, 10):
        notes.append("the target tin is much smaller; batter will be deeper and may need longer, or use a smaller batch")
    elif factor > Fraction(13, 10):
        notes.append("the target tin is much larger; batter will be shallower, so check for doneness earlier")
    if source.shape == "round" and target.shape == "round":
        notes.append("round-to-round ratios are exact: pi cancels")
    elif source.shape != target.shape:
        notes.append("mixed shapes: the ratio uses pi to fifteen places and is an approximation")
    return factor, notes
