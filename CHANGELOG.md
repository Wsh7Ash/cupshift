# Changelog

All notable changes to this project are recorded here. The format follows
Keep a Changelog, and the version follows semantic versioning.

## [1.0.0] - 2026-11-03

### Added

- `cupshift scale` with factor or target-servings scaling, metric output, and
  text, markdown, JSON and HTML formats.
- `cupshift convert` with density-aware volume/mass conversion in both directions.
- `cupshift pan` for area and volume factors between round, square and
  rectangular tins.
- `cupshift parse` for inspecting how one ingredient line was understood.
- Exact rational arithmetic for every quantity, with ASCII mixed-number output.
- Unit registry for volume, mass and count families, including butter sticks and
  approximate units (pinch, dash).
- Ingredient density table with longest-key matching, and a named error when a
  density is missing rather than a silent default.
- Practical rounding: eighths and thirds for volume, 1/5/10 g steps for mass,
  half-millilitre steps for small metric volumes.
- Unit ascent (3 tsp → 1 tbsp, 4 tbsp → 1/4 cup, 1000 g → 1 kg).
- Flags for leavening, seasoning and fractional eggs.
- A plain-text recipe format with ranges, package sizes, preparation notes and
  unscalable phrases.
- 87 tests covering arithmetic exactness, parsing, rounding boundaries, pan
  geometry, rendering and the CLI exit-code contract.
- GitHub Actions CI on Python 3.11 and 3.12.

### Fixed

- Units pluralise above one (`4 cups`) and stay singular for fractions
  (`1/4 cup`).
- The card's grams column and `convert --to g` now share one rounding path, so
  the same ingredient cannot report two weights.
- Mixed-shape pan factors print as decimals instead of sixteen-digit rationals;
  round-to-round factors stay exact (`64/81`).
- Metric volumes below 10 ml round to half a millilitre, so a half teaspoon is
  `2 1/2 ml` rather than `0 ml`.
