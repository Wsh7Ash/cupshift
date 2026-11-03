"""Command line interface for cupshift.

Exit codes are part of the contract: ``0`` success, ``1`` a data problem the user
can fix (unreadable recipe, unknown unit, missing density), ``2`` a usage error
raised by argparse before any work happens.
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

from . import __version__
from .pan import PanError, pan_factor, parse_pan
from .parse import ParseError, parse_ingredient, parse_quantity, parse_recipe_file
from .render import render_html, render_markdown, render_text
from .scale import ScaleError, format_quantity, round_value, scale_recipe
from .units import UnitError, convert, density_for, lookup

__all__ = ["build_parser", "main"]


def _single_number(text: str, label: str) -> Fraction:
    low, high, rest = parse_quantity(text)
    if low is None or high is not None or rest:
        raise ScaleError(f"{label} must be a single number, got {text!r}")
    return low


def _write(text: str, destination: str | None) -> None:
    if destination:
        Path(destination).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {destination}")
    else:
        print(text)


def _cmd_scale(args: argparse.Namespace) -> int:
    recipe = parse_recipe_file(args.recipe)
    factor = _single_number(args.factor, "--factor") if args.factor else None
    target = _single_number(args.servings, "--servings") if args.servings else None
    scaled = scale_recipe(recipe, factor=factor, target_servings=target, metric=args.metric)

    if args.format == "json":
        text = json.dumps(scaled.as_dict(), indent=2, ensure_ascii=True)
    elif args.format == "markdown":
        text = render_markdown(scaled)
    elif args.format == "html":
        text = render_html(scaled)
    else:
        text = render_text(scaled)
    _write(text, args.out)
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    source = lookup(args.unit)
    if source is None:
        raise UnitError(f"unknown unit: {args.unit!r}")
    target = lookup(args.to)
    if target is None:
        raise UnitError(f"unknown target unit: {args.to!r}")

    quantity = _single_number(args.amount, "amount")
    density: Fraction | None = None
    matched: str | None = None
    if args.density:
        density = _single_number(args.density, "--density")
    elif args.ingredient:
        density, matched = density_for(args.ingredient)
        if density is None and {source.family, target.family} == {"volume", "mass"}:
            raise UnitError(
                f"no density known for {args.ingredient!r}; pass --density in grams per millilitre"
            )

    result = round_value(convert(quantity, source, target, density), target)
    line = f"{format_quantity(result)} {target.name}"
    detail: list[str] = []
    if density is not None and source.family != target.family:
        detail.append(f"density {float(density):g} g/ml" + (f" ({matched})" if matched else ""))
    if detail:
        line += "  (" + ", ".join(detail) + ")"
    print(line)
    return 0


def _cmd_pan(args: argparse.Namespace) -> int:
    source = parse_pan(args.source)
    target = parse_pan(args.target)
    depth_from = _single_number(args.depth_from, "--depth-from") if args.depth_from else None
    depth_to = _single_number(args.depth_to, "--depth-to") if args.depth_to else None
    factor, notes = pan_factor(source, target, depth_from, depth_to)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "factor": format_quantity(factor),
                    "factor_value": round(float(factor), 4),
                    "source": {"shape": source.shape, "width_cm": str(source.width_cm)},
                    "target": {"shape": target.shape, "width_cm": str(target.width_cm)},
                    "notes": notes,
                },
                indent=2,
            )
        )
        return 0

    # A round-to-round factor is a clean rational (64/81) and worth printing as
    # one. A mixed-shape factor divides by an approximation of pi, so its exact
    # form is a sixteen-digit rational that no cook wants to read: print a
    # decimal instead.
    if factor.denominator <= 100:
        label = f"{format_quantity(factor)}x  ({float(factor):.3f})"
        multiplier = format_quantity(factor)
    else:
        label = f"{float(factor):.3f}x"
        multiplier = f"{float(factor):.3f}"

    print(f"factor {label}")
    print(f"multiply every ingredient by {multiplier}")
    for note in notes:
        print(f"  - {note}")
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    ingredient = parse_ingredient(args.line)
    print(
        json.dumps(
            {
                "raw": ingredient.raw,
                "quantity": format_quantity(ingredient.quantity) if ingredient.quantity else None,
                "quantity_high": format_quantity(ingredient.quantity_high)
                if ingredient.quantity_high
                else None,
                "unit": str(ingredient.unit) if ingredient.unit else None,
                "family": ingredient.unit.family if ingredient.unit else None,
                "name": ingredient.name,
                "note": ingredient.note,
                "package": ingredient.package,
                "unscalable": ingredient.unscalable,
                "reason": ingredient.reason,
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cupshift",
        description="Scale recipes with exact unit algebra, densities and pan geometry.",
    )
    parser.add_argument("--version", action="version", version=f"cupshift {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scale = subparsers.add_parser("scale", help="scale a recipe file")
    scale.add_argument("recipe", help="path to a recipe file")
    scale.add_argument("--factor", help="multiply every quantity by this number")
    scale.add_argument("--servings", help="target number of servings")
    scale.add_argument("--metric", action="store_true", help="convert volumes to ml and masses to g")
    scale.add_argument(
        "--format",
        choices=("text", "json", "markdown", "html"),
        default="text",
        help="output format (default: text)",
    )
    scale.add_argument("--out", help="write to this path instead of stdout")
    scale.set_defaults(func=_cmd_scale)

    convert_cmd = subparsers.add_parser("convert", help="convert one quantity between units")
    convert_cmd.add_argument("amount", help="quantity, e.g. 2 or 1 1/2")
    convert_cmd.add_argument("unit", help="source unit, e.g. cups")
    convert_cmd.add_argument("ingredient", nargs="?", default="", help="ingredient name, for density lookup")
    convert_cmd.add_argument("--to", required=True, help="target unit, e.g. g")
    convert_cmd.add_argument("--density", help="grams per millilitre, overriding the lookup")
    convert_cmd.set_defaults(func=_cmd_convert)

    pan = subparsers.add_parser("pan", help="factor between two tin sizes")
    pan.add_argument("--from", dest="source", required=True, help="source tin, e.g. '9in round'")
    pan.add_argument("--to", dest="target", required=True, help="target tin, e.g. '8x8in square'")
    pan.add_argument("--depth-from", dest="depth_from", help="source depth in cm, optional")
    pan.add_argument("--depth-to", dest="depth_to", help="target depth in cm, optional")
    pan.add_argument("--format", choices=("text", "json"), default="text")
    pan.set_defaults(func=_cmd_pan)

    parse_cmd = subparsers.add_parser("parse", help="show how one ingredient line is parsed")
    parse_cmd.add_argument("line", help="an ingredient line, quoted")
    parse_cmd.set_defaults(func=_cmd_parse)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (UnitError, ParseError, ScaleError, PanError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
