"""Rendering and the command line contract, including exit codes."""

from __future__ import annotations

import json
from fractions import Fraction as F
from pathlib import Path

import pytest

from cupshift.cli import main
from cupshift.parse import parse_recipe
from cupshift.render import render_html, render_markdown, render_text
from cupshift.scale import scale_recipe

REPO_ROOT = Path(__file__).resolve().parents[1]


def scaled(*lines: str, factor: str = "2"):
    body = "\n".join(lines)
    recipe = parse_recipe(f"title: Test Card\nservings: 2\n\n## ingredients\n{body}\n")
    return scale_recipe(recipe, factor=F(factor))


def test_text_output_has_a_header_and_a_grams_column():
    text = render_text(scaled("1 cup all-purpose flour"))
    assert "Test Card" in text
    assert "factor 2x" in text
    assert "250 g" in text


def test_text_output_lists_flags():
    text = render_text(scaled("1 tsp baking powder"))
    assert "leavening does not scale linearly" in text


def test_markdown_output_is_a_table():
    text = render_markdown(scaled("1 cup milk"))
    assert text.startswith("### Test Card")
    assert "| Ingredient | Amount | Grams | Note |" in text


def test_html_output_escapes_recipe_text():
    text = render_html(scaled("1 cup <script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text


def test_html_output_is_self_contained():
    text = render_html(scaled("1 cup milk"))
    assert text.startswith("<!doctype html>")
    assert "<style>" in text


def test_cli_parse_prints_json(capsys):
    assert main(["parse", "1 1/2 cups flour"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["quantity"] == "1 1/2"
    assert payload["unit"] == "cup"
    assert payload["name"] == "flour"


def test_cli_scale_runs_on_the_shipped_example(capsys):
    assert main(["scale", str(REPO_ROOT / "examples" / "pancakes.recipe"), "--factor", "2"]) == 0
    out = capsys.readouterr().out
    assert "Buttermilk Pancakes" in out
    assert "4 cups" in out


def test_cli_scale_writes_json_to_a_file(tmp_path, capsys):
    target = tmp_path / "card.json"
    code = main(
        [
            "scale",
            str(REPO_ROOT / "examples" / "tomato-soup.recipe"),
            "--servings",
            "6",
            "--format",
            "json",
            "--out",
            str(target),
        ]
    )
    assert code == 0
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["target_servings"] == "6"
    assert payload["factor"] == "1 1/2"


def test_cli_missing_recipe_exits_one(capsys):
    assert main(["scale", "no-such.recipe", "--factor", "2"]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_convert_uses_the_density_table(capsys):
    assert main(["convert", "2", "cups", "flour", "--to", "g"]) == 0
    out = capsys.readouterr().out
    assert "250 g" in out
    assert "density 0.53" in out


def test_cli_convert_rejects_an_unknown_unit(capsys):
    assert main(["convert", "1", "smidgen", "--to", "g"]) == 1
    assert "unknown unit" in capsys.readouterr().err


def test_cli_convert_without_a_density_exits_one(capsys):
    assert main(["convert", "1", "cups", "unobtainium", "--to", "g"]) == 1
    assert "no density" in capsys.readouterr().err


def test_cli_pan_prints_a_factor(capsys):
    assert main(["pan", "--from", "9in round", "--to", "8in round"]) == 0
    out = capsys.readouterr().out
    assert "factor 64/81x" in out
    assert "0.790" in out


def test_cli_pan_mixed_shapes_print_a_decimal_not_a_giant_rational(capsys):
    assert main(["pan", "--from", "9in round", "--to", "8x8in square"]) == 0
    out = capsys.readouterr().out
    assert "factor 1.006x" in out
    assert "5059226767" not in out


def test_cli_pan_json(capsys):
    assert main(["pan", "--from", "9in round", "--to", "9in round", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["factor"] == "1"


def test_cli_unknown_command_is_a_usage_error():
    with pytest.raises(SystemExit) as caught:
        main(["frobnicate"])
    assert caught.value.code == 2
