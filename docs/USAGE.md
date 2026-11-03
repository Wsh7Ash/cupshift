# Usage

## Install

```shell
python -m pip install -e "."
```

or run from the source tree without installing:

```shell
PYTHONPATH=src python -m cupshift --version
```

## The four commands

### `scale`

```shell
cupshift scale RECIPE (--factor N | --servings N) [--metric] [--format F] [--out PATH]
```

| Flag | Meaning |
|---|---|
| `--factor` | multiply every quantity by this number; accepts `1.5`, `3/2`, `1 1/2` |
| `--servings` | target servings, using the recipe's declared `servings:` |
| `--metric` | convert volumes to millilitres and masses to grams before rounding |
| `--format` | `text` (default), `markdown`, `json`, `html` |
| `--out` | write to a file instead of stdout |

Exactly one of `--factor` and `--servings` is required. A recipe without a
`servings:` header cannot be scaled by target; use `--factor`.

### `convert`

```shell
cupshift convert AMOUNT UNIT [INGREDIENT] --to UNIT [--density G_PER_ML]
```

```shell
$ cupshift convert 2 cups flour --to g
250 g  (density 0.53 g/ml (flour))

$ cupshift convert 100 g butter --to cups
1/2 cup  (density 0.9593 g/ml (butter))

$ cupshift convert 3 tsp --to tbsp
1 tbsp

$ cupshift convert 1 cup milk --to g --density 1.02
245 g  (density 1.02 g/ml)
```

Same-family conversion never needs a density. Cross-family conversion needs one,
either from the ingredient name or from `--density`; without it the command exits
1 with a message naming the ingredient.

### `pan`

```shell
cupshift pan --from "9in round" --to "8x8in square" [--depth-from CM --depth-to CM] [--format json]
```

Accepted geometries: `9in round`, `20cm round`, `8x8in square`, `9x13 in`,
`9" round`, `200mm round`. With both depths, the factor is a volume ratio;
without them it is an area ratio and the tool says so.

A factor below 0.7 or above 1.3 adds a warning: batter depth changes enough that
baking time usually has to change too. The tool will not guess the new time.

### `parse`

```shell
$ cupshift parse "1 (14 oz) can chopped tomatoes"
{
  "raw": "1 (14 oz) can chopped tomatoes",
  "quantity": "1",
  "quantity_high": null,
  "unit": "can",
  "family": "count",
  "name": "chopped tomatoes",
  "note": null,
  "package": "14 oz",
  "unscalable": false,
  "reason": null
}
```

Useful when a line scales in a way you did not expect: it shows exactly which
text became the quantity, the unit, the name and the package.

## Recipe format

```text
title: Name of the dish
servings: 4

## ingredients
<one ingredient per line>

## method
<free text, kept verbatim>
```

Rules:

- Header lines before the first section must be `title:` or `servings:` (or a
  `# Title` line). Anything else is an error with a line number.
- `## ingredients` is required and must contain at least one parseable line.
- `## method`, `## directions`, `## steps` and `## preparation` are all accepted.
- Lines starting with `//` are comments.

### Ingredient line shapes

| Line | Understood as |
|---|---|
| `2 cups all-purpose flour` | 2 cups, flour |
| `1 1/2 tsp baking powder` | 3/2 tsp |
| `1½ tsp salt` | 3/2 tsp (unicode fraction) |
| `0.5 cup milk` | 1/2 cup |
| `2-3 tbsp olive oil` | range 2..3 |
| `1 to 2 cloves garlic` | range 1..2, unit clove |
| `1 (14 oz) can tomatoes` | 1 can, package 14 oz |
| `a pinch of cayenne` | 1 pinch |
| `1 onion, finely chopped` | name onion, note finely chopped |
| `salt to taste` | unscalable, rendered as written |
| `800 g flour` | mass |

Lines with no name (`2 cups`) and fractions with a zero denominator (`1/0 cup`)
are rejected with a message.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | fixable data problem: unreadable file, unknown unit, missing density, bad factor |
| 2 | usage error (argparse), e.g. an unknown subcommand |

## Extending the density table

Add a line to `_DENSITY_TABLE` in `src/cupshift/units.py`:

```python
("rye flour", _f("0.55")),
```

Keys are matched case-insensitively as whole words inside the ingredient name,
and the longest key wins. Add a test in `tests/test_units.py` asserting the
conversion you expect, because a wrong density is silent: the tool will happily
convert with it.

## Interpreting a card

- `amount` is what you measure; `grams` is the same quantity weighed, present
  only when a density is known or the unit is already mass.
- `notes` lists the flags that matter: leavening, seasoning, fractional eggs.
- `scaling` restates the factor and the serving change, so a printed card carries
  its own provenance.
- Rows marked `as written` were vague in the original recipe and were deliberately
  not multiplied.
