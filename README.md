# cupshift

Scale a recipe for a different number of people, or a different tin, without
doing arithmetic on your phone — and without quietly ruining the result.

## The problem

Recipe scaling is not multiplication, and the ways it goes wrong are invisible
until the cake is out of the oven:

- **A cup is not a unit of mass.** One cup of flour is about 125 g, one cup of
  sugar about 200 g, one cup of water 237 g. Any tool that treats a cup as a
  fixed weight is wrong for almost every ingredient.
- **Fractions have to stay fractions.** Doubling 2/3 cup is 4/3 cup, printed as
  `1 1/3`, not `1.3333334`. A recipe card with a decimal on it is a card a cook
  will mis-measure.
- **Some things do not scale linearly.** Leavening, salt and spice behave
  non-linearly in practice, and eggs cannot be divided into thirds.
- **A different tin is a different bake.** A 9-inch round tin and an 8-inch
  square tin hold within four percent of the same batter — and the difference is
  area, not diameter.
- **Vague amounts are amounts.** "Salt to taste" and "a pinch" must survive
  scaling instead of being multiplied into nonsense.

## What it does

| Command | Purpose |
|---|---|
| `cupshift scale RECIPE` | scale by factor or target servings, with optional metric output |
| `cupshift convert 2 cups flour --to g` | one quantity, density-aware, in either direction |
| `cupshift pan --from "9in round" --to "8in round"` | factor between two tins, by area or volume |
| `cupshift parse "1 (14 oz) can tomatoes"` | see exactly how a line was understood |

Every quantity is an exact `Fraction`. Volume-to-mass conversion requires a
density for the named ingredient, and a missing density is a named error rather
than a guess.

## Representative output

`python -m cupshift scale examples/pancakes.recipe --servings 12`:

```text
Buttermilk Pancakes  (factor 1 1/2x, servings 8 -> 12)

ingredient         amount         grams
-----------------  -------------  -----
all-purpose flour  3 cups         375 g
buttermilk         2 5/8 cups     640 g
baking powder      2 1/4 tsp      10 g
baking soda        3/4 tsp        4 g
granulated sugar   3 tbsp         37 g
salt               1 1/2 tsp      9 g
large eggs         3
butter             1/4 cup        57 g
nutmeg             1 1/2 pinches

notes
  - baking powder: leavening does not scale linearly; check the rise and texture
  - baking soda: leavening does not scale linearly; check the rise and texture
  - salt: season to taste after scaling rather than trusting the arithmetic
  - nutmeg: season to taste after scaling rather than trusting the arithmetic

scaling
  - servings 8 -> 12
  - factor 1 1/2x
```

`python -m cupshift pan --from "9in round" --to "8in round"`:

```text
factor 64/81x  (0.790)
multiply every ingredient by 64/81
  - factor is the area ratio, assuming the same filling depth
  - round-to-round ratios are exact: pi cancels
```

## How the arithmetic works

1. **Exact rationals.** `fractions.Fraction` everywhere in the quantity path.
   Three teaspoons convert to one tablespoon exactly, not to 0.9999999.
2. **Units by family.** Volume (base ml), mass (base g), count (base each).
   Within a family, conversion is a multiplication.
3. **Density for the crossing.** Volume to mass uses a documented grams-per-ml
   value per ingredient (`flour 0.53`, `sugar 0.845`, `honey 1.42`, …), with the
   longest matching key winning: "brown sugar" beats "sugar". Unknown ingredient
   → error, not a default.
4. **Practical rounding.** Volumes round to eighths, quarters, thirds and halves;
   masses round in 1 g, 5 g or 10 g steps by magnitude; metric volumes round in
   half-millilitre, 5 ml or 50 ml steps.
5. **Unit ascent.** 3 tsp becomes 1 tbsp, 4 tbsp becomes 1/4 cup, 1000 g becomes
   1 kg. A range such as `2-3 tbsp` keeps its unit, because ascending it would
   produce a range nobody wants to measure.
6. **Flags instead of false confidence.** Fractional eggs, leavening and
   seasoning are marked in the output with the reason.

## Requirements

- Python 3.10 or newer (standard library only at runtime).
- pytest to run the suite.

## Installation

```shell
git clone https://github.com/Wsh7Ash/cupshift
cd cupshift
python -m pip install -e ".[dev]"
```

Without installing, everything works from the source tree:

```shell
PYTHONPATH=src python -m cupshift --version
```

## Quick start

```shell
cupshift scale examples/pancakes.recipe --servings 12
cupshift scale examples/tomato-soup.recipe --factor 3 --format markdown
cupshift convert 2 cups flour --to g
cupshift pan --from "9in round" --to "8x8in square"
python -m pytest -q
```

## Usage

### Scaling

```shell
cupshift scale examples/pancakes.recipe --servings 12
cupshift scale examples/pancakes.recipe --factor 1.5
cupshift scale examples/pancakes.recipe --factor 3/2 --format json
cupshift scale examples/pancakes.recipe --servings 12 --metric
cupshift scale examples/pancakes.recipe --servings 12 --format html --out card.html
```

Exactly one of `--factor` or `--servings` is required. `--metric` converts
volumes to millilitres and masses to grams before rounding. Formats: `text`
(default), `markdown`, `json`, `html`.

### Converting one quantity

```shell
$ cupshift convert 2 cups flour --to g
250 g  (density 0.53 g/ml (flour))

$ cupshift convert 100 g butter --to cups
1/2 cup  (density 0.9593 g/ml (butter))
```

`--density 0.9` overrides the lookup for an ingredient the table does not know.

### Pan conversion

```shell
$ cupshift pan --from "9in round" --to "8in round"
factor 64/81x  (0.790)
multiply every ingredient by 64/81
  - factor is the area ratio, assuming the same filling depth
  - round-to-round ratios are exact: pi cancels
```

Add `--depth-from 2 --depth-to 3` (centimetres) to convert by volume instead of
area. A factor outside 0.7–1.3 prints a warning about batter depth, because that
is the range where baking time usually has to change.

## Recipe format

Plain text, no proprietary document:

```text
title: Buttermilk Pancakes
servings: 8

## ingredients
2 cups all-purpose flour
1 1/2 tsp baking powder
2 large eggs
a pinch of nutmeg
salt to taste

## method
Whisk the dry ingredients, then fold in the wet ones.
```

Ingredient lines accept integers, decimals, fractions, mixed numbers, unicode
fractions (`1½`), ranges (`2-3`, `1 to 2`), package sizes (`1 (14 oz) can`),
preparation notes after a comma, and vague amounts (`a pinch`, `to taste`).

## Configuration

None. There is no config file, no environment variable and no network access.
The density table is a readable constant in `src/cupshift/units.py`
(`_DENSITY_TABLE`); adding an ingredient is a one-line change plus a test.

## Testing

```shell
python -m pytest -q
```

87 tests: unit algebra (exactness of tsp/tbsp/cup and lb/oz), density lookups and
their precedence, every accepted quantity shape, the shapes that must be
rejected, scaling and rounding boundaries, unit ascent, egg and leavening flags,
pan geometry including the exact 64/81 round-to-round ratio, HTML escaping, and
the CLI exit-code contract.

## Project structure

```text
cupshift/
├─ src/cupshift/
│  ├─ units.py      unit registry, exact conversions, density table
│  ├─ parse.py      ingredient and recipe parsing
│  ├─ scale.py      scaling, rounding, ascent, flags
│  ├─ pan.py        pan geometry and tin factors
│  ├─ render.py     text, markdown, html
│  └─ cli.py        argparse front end, exit codes
├─ tests/           87 tests
├─ examples/        two synthetic recipes
├─ results/         observed output for every command in RESULTS.md
├─ docs/            ARCHITECTURE.md, USAGE.md, PROJECT_SPEC.md
├─ RESULTS.md       what was actually executed
└─ CHANGELOG.md
```

## Limitations

- **Densities are approximations of physical ingredients.** Flour compacts; a
  scooped cup and a spooned cup differ by up to twenty percent. The tool prints
  the density it used so the assumption is visible.
- **Rounding is a cooking decision, not a mathematical one.** `5/8 cup` is exact
  and awkward; the tool keeps eighths because that is what measuring cups have.
- **Egg splitting is guidance, not precision.** A large egg is about 50 g; the
  flag says to weigh the fraction rather than pretending the arithmetic is exact.
- **Leavening and seasoning are flagged, not adjusted.** No formula replaces
  judgement about your oven, pan and taste.
- **Vague units stay vague.** `1 1/2 pinches` is a faithful scaling of `a pinch`
  and is not a measurement.
- **No nutrition, costing or shopping-list features.** A different tool.

## Roadmap

- A `--density-file` flag to load a user's own ingredient table.
- Oven-temperature and time guidance when a pan factor is outside 0.7–1.3.
- Recipe import from common plain-text formats (Markdown lists, `cooklang`),
  with the same parser underneath.

## Security notes

No network access, no subprocesses, no evaluation of recipe content. Recipe files
are untrusted text: HTML output escapes every ingredient name, note and package
string, and the parser rejects rather than executes anything it does not
understand. The tool writes only the path given to `--out`.

## License

MIT. See [LICENSE](LICENSE).
