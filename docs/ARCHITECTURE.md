# Architecture

## Shape

```text
                 recipe text
                      │
                 parse.py ──────────────► Recipe(title, servings, [Ingredient])
                      │                              │
                      │                              │  Ingredient(quantity, unit, name, note, package, flags)
                      ▼                              ▼
                 units.py ◄────────────── scale.py (factor, rounding, ascent, flags)
                 registry,                   │
                 densities,                  ▼
                 conversion             ScaledRecipe([ScaledItem])
                      ▲                       │
                      │                       ▼
                 pan.py ──────────────► render.py (text | markdown | html)
                 (geometry)                  │
                                             ▼
                                          cli.py
```

`pan.py` is independent of the recipe path: it answers a geometric question and
returns a factor a user can apply to any recipe, including one that is not in a
file.

## Modules

### `units.py`

- `Unit(name, family, factor)` where `factor` converts to the family base unit
  (millilitre for volume, gram for mass, each for count).
- `UNITS` is a flat alias registry, so `cups`, `cup` and `cups.` resolve to one
  `Unit`. Plural handling is explicit (an `-s`/`-es` fallback) rather than a
  guess.
- `convert(quantity, source, target, density)` is total for same-family pairs and
  raises `DensityError` for a volume/mass pair with no density.
- `density_for(name)` returns `(grams_per_ml, matched_key)` and resolves the
  *longest* matching key, which is what makes "brown sugar" win over "sugar".

### `parse.py`

- `parse_quantity(text)` recognises mixed numbers, unicode fractions, plain
  fractions, decimal values and ranges, in that order, and returns the remainder
  untouched so the caller knows exactly what it consumed.
- `parse_ingredient(line)` walks the remainder: parenthetical package size, then
  unit (with `fl oz` handled as a two-token unit), then a second package, then the
  name, then a preparation note after the last comma.
- Unscalable phrases (`to taste`, `as needed`, `for garnish`, …) are removed
  before parsing and recorded with a reason, so the row renders as written
  instead of being multiplied.
- `parse_recipe` is line-oriented and strict about anything before the first
  section header: a stray sentence is an error with a line number, not a silent
  skip.

### `scale.py`

Three decisions carry the product:

1. **Exact arithmetic.** `Fraction` throughout; `format_quantity` renders an
   ASCII mixed number (`1 1/3`) for print and JSON.
2. **Rounding by family and magnitude.** `round_value` dispatches to eighths and
   thirds for volume, to 1/5/10 g steps for mass, to half-millilitre/5/50 ml
   steps for metric volume, and to halves for counts.
3. **Ascent before rounding.** `ascend` moves up while the quantity exceeds the
   next unit's threshold (3 tsp → 1 tbsp, 4 tbsp → 1 cup, 1000 g → 1 kg), with
   the threshold chosen so the result is a quantity a cook would write down. A
   range is exempt, because ascending `2-3 tbsp` produces a range nobody measures.

Flags are attached per item: leavening (non-linear), seasoning (taste), and a
fractional egg (weigh the part). Flags are strings, not booleans, because the
reason is the useful part.

### `pan.py`

- Parse `9in round`, `20cm round`, `8x8in square`, `9x13 in`, `9" round`.
- Areas are exact rationals; a round tin's area carries a rational approximation
  of pi, which cancels exactly in a round-to-round ratio (hence `64/81`, not
  `0.7901234`).
- `pan_factor` returns the area ratio, or the volume ratio when both depths are
  given, plus notes for the two cases that need a warning: a factor below 0.7 or
  above 1.3 changes batter depth enough to change baking time.

### `render.py`

Four formats over one `ScaledRecipe`. Text is column-aligned; markdown is a
table; HTML is self-contained with every recipe string escaped; JSON is the
dataclass projection. All output is ASCII-safe apart from the HTML, which is
UTF-8 and declares it.

### `cli.py`

`argparse` with four subcommands. The exit-code contract is explicit and tested:

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | data problem the user can fix (unreadable file, unknown unit, missing density, bad factor) |
| 2 | usage error raised by argparse before any work |

## Invariants

1. No float in the quantity path. `float` appears only in JSON for display and in
   the pan CLI's decimal formatting.
2. A conversion never invents a density. Missing density is an error naming the
   ingredient.
3. An ingredient line is either parsed completely or rejected with a line
   number; nothing is dropped silently.
4. Rendering never mutates the scaled model, so the same `ScaledRecipe` can be
   rendered in all four formats with identical numbers.

## Testing strategy

- One test per arithmetic relationship that must be exact (3 tsp = 1 tbsp,
  16 tbsp = 1 cup, 1 lb = 16 oz, 9in → 8in round = 64/81).
- One test per accepted quantity shape, and one per rejected shape.
- Boundary tests for rounding and ascent rather than only mid-range values.
- A test that the card and the converter agree on grams, which is the regression
  for defect 2 in `RESULTS.md`.
- A test that a small metric volume does not round to zero, the regression for
  defect 4.
- CLI tests through `main(argv)` asserting exit codes and observable output, with
  no subprocess and no network.
