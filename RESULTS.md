# Results

Every number and every quoted line below comes from a command run on the machine
that built this repository. Nothing here is projected.

## Environment

- OS: Windows (win32), Git Bash for the shell commands
- Runtime: Python 3.14.3
- Dependency manager: pip (the package declares no runtime dependencies)
- Git: 2.55.0.windows.3
- Entry points: `python -m cupshift` from the source tree, and the `cupshift`
  console script after an editable install

The system interpreter on this machine is marked externally managed (PEP 668),
so `pip install` into it is refused. The install gate therefore runs in a
repository-local `.venv`. A first attempt with `--no-build-isolation` failed
with `BackendUnavailable: Cannot import 'setuptools.build_meta'` because the base
interpreter ships no setuptools; with build isolation left on, the install
completed and produced `.venv/bin/cupshift`. Recreating that venv is what the
commands below do.

## Validation performed

| Gate | Result |
|---|---|
| dependency installation | PASS — editable install into a local venv; the console script ran and the suite passed inside it (see the PEP 668 note below) |
| build (wheel/sdist) | N/A — pure-Python package, no compile step |
| unit tests | PASS — 87 collected, 87 passed |
| lint | N/A — no linter configured for this repository |
| type check | N/A — no type checker configured |
| demo run (all four subcommands) | PASS |
| README commands | PASS — each command in the README was run; output quoted below |
| secret scan | PASS — no credential-shaped assignment in the tree |

## Commands executed

```shell
cd projects/2026-11-03/cupshift

python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/cupshift --version
.venv/bin/python -m pytest -q

PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m pytest --collect-only -q

PYTHONPATH=src python -m cupshift scale examples/pancakes.recipe --servings 12
PYTHONPATH=src python -m cupshift scale examples/pancakes.recipe --servings 12 --format json
PYTHONPATH=src python -m cupshift scale examples/pancakes.recipe --servings 12 --format html \
  --out results/pancakes-card.html
PYTHONPATH=src python -m cupshift scale examples/pancakes.recipe --servings 8 --metric
PYTHONPATH=src python -m cupshift scale examples/tomato-soup.recipe --factor 3 --format markdown

PYTHONPATH=src python -m cupshift convert 2 cups flour --to g
PYTHONPATH=src python -m cupshift pan --from "9in round" --to "8in round"
PYTHONPATH=src python -m cupshift pan --from "9in round" --to "8x8in square"
PYTHONPATH=src python -m cupshift parse "1 (14 oz) can chopped tomatoes"

grep -rInE "(api[_-]?key|secret|passwd|password|token)[[:space:]]*[:=][[:space:]]*['\"][^'\"]+" \
  --include="*.py" --include="*.md" --include="*.yml" --include="*.toml" .
```

## Observed result

`pytest`:

```text
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 0.29s
```

`scale --servings 12` on the pancake recipe, the full card:

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

`scale --metric`, which is the case that exposed the rounding defect below:

```text
Buttermilk Pancakes  (factor 1x, servings 8 -> 8)

ingredient         amount    grams
-----------------  --------  -----
all-purpose flour  475 ml    250 g
buttermilk         415 ml    425 g
baking powder      7 1/2 ml  7 g
baking soda        2 1/2 ml  3 g
granulated sugar   30 ml     25 g
salt               5 ml      6 g
large eggs         2
butter             45 ml     43 g
nutmeg             1/2 ml
```

`pan`, both shapes:

```text
factor 64/81x  (0.790)
multiply every ingredient by 64/81
  - factor is the area ratio, assuming the same filling depth
  - round-to-round ratios are exact: pi cancels
```

```text
factor 1.006x
multiply every ingredient by 1.006
  - factor is the area ratio, assuming the same filling depth
  - mixed shapes: the ratio uses pi to fifteen places and is an approximation
```

`convert` and `parse`:

```text
250 g  (density 0.53 g/ml (flour))
```

```json
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

Secret scan: no matches. The pattern is shown above so a reader can run exactly
the same grep rather than trusting the word "clean".

## Defects found and fixed during the build

These were found by running the tool, not by reading it. Each is recorded because
the fix is the evidence that the gate did something.

1. **A plural that was not a plural.** The card printed `4 cup`. The unit label
   now pluralises for quantities greater than one — and deliberately does not for
   `1/4 cup`, because English keeps a fraction singular. Abbreviations (`tbsp`,
   `ml`, `g`) never pluralise.
2. **The card and the converter disagreed by one gram.** The card rounded grams
   to the nearest integer (501.57 → 502 g) while `convert --to g` used the 5 g
   step (250). Both now use the same `round_value` path, so the same ingredient
   cannot report two different weights in one tool.
3. **A sixteen-digit rational printed to a cook.** A mixed-shape pan factor
   divided by an approximation of pi and printed
   `factor 1 1530995059226767/254469004940773233x`. Factors whose denominator is
   small stay as fractions (`64/81`, exact and readable); anything else prints to
   three decimals.
4. **A half teaspoon became zero millilitres.** Metric rounding used a 5 ml step
   for everything under a litre, so `1/2 tsp` rounded to `0 ml` on a real card.
   Volumes below 10 ml now round to half a millilitre, and the same recipe prints
   `2 1/2 ml`.
5. **A duplicated title in markdown.** The card emitted `### Title` followed by
   an italic line that repeated the title. The italic line now carries only the
   factor and serving change.

Two test expectations were also wrong during development and were corrected
rather than accommodated: one asserted `4 cup`, the other asserted the old 502 g
figure. In both cases the code was right and the test described the bug.

## Generated artifacts

- `results/pancakes-scaled.txt` — full text card, servings 8 → 12
- `results/pancakes-scaled.json` — the same card as structured JSON
- `results/pancakes-card.html` — self-contained HTML card
- `results/pancakes-metric.txt` — metric output, no scaling
- `results/soup-tripled.md` — markdown card at factor 3
- `results/pan-round-to-round.txt` — 9in → 8in round, exact 64/81
- `results/pan-round-to-square.txt` — 9in round → 8x8in square, decimal factor
- `results/convert-flour.txt` — density-aware conversion
- `results/parse-can.txt` — parsed package-size line

## Not performed, and why

- **No linter or type checker.** None is configured, so the honest entry is N/A
  rather than PASS.
- **No wheel or sdist.** The package has no compile step and no runtime
  dependency. The editable install in the venv is the install gate that matters
  here; `build` was not run because nothing would be published from it.
- **No real-kitchen validation.** The recipes are synthetic and were written for
  the tests; the tool's output was checked against arithmetic and against the
  density table, not against a baked cake. That limit is stated in the README.
