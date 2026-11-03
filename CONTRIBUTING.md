# Contributing

## Before you start

- Run the suite: `PYTHONPATH=src python -m pytest -q` (87 tests, no network, no
  external services).
- Read `docs/ARCHITECTURE.md`, particularly the invariants section. A patch that
  introduces a float into the quantity path will be rejected regardless of how
  well it works for one example.

## Ground rules

1. **Quantities stay `Fraction`.** Convert at the edge (`--factor 1.5` parses to
   `3/2`) and keep rationals through rounding and rendering.
2. **No invented densities.** A new ingredient density needs a stated source or a
   note explaining the measurement; a guessed value is worse than an error
   because it fails silently.
3. **No silent drops.** A parser that cannot understand a line must raise with the
   line number.
4. **Rounding is a product decision.** Changing a step changes what a cook
   measures, so a rounding change needs a test that names the cooking case it
   fixes.
5. **Every fix gets a regression test.** The four defects in `RESULTS.md` each
   have one; new defects should follow the same pattern.

## Adding a unit

1. Add an entry to `_VOLUME`, `_MASS` or `_COUNT` in `src/cupshift/units.py` with
   its factor to the family base unit.
2. Add aliases, including the plural if it is irregular.
3. If the label changes with quantity, add it to `PLURAL_UNITS` in `scale.py`.
4. Add a test asserting a conversion that must be exact, not approximate.

## Adding a density

1. Add `("<ingredient key>", _f("<grams per ml>"))` to `_DENSITY_TABLE`.
2. Add a test that one cup converts to the gram figure you expect, with a
   tolerance that reflects how the ingredient is actually measured.
3. If the key would shadow a shorter one, add a test for the precedence.

## Style

- Standard library only at runtime. A dependency needs a strong reason.
- Type hints on public functions.
- Docstrings explain *why*, not what the code already says.
- ASCII in source and output; unicode is accepted on input.

## Reporting a problem

Open an issue with the recipe line, the command, the observed output and the
output you expected. A failing test case is the most useful report.
