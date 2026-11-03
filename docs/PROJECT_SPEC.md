# Project specification

## Name

`cupshift`

## Category

`productivity` — a small tool a non-developer can use on the same day, with real
engineering underneath.

## Target user

A home cook who wants to cook a recipe for a different number of people, or in a
different tin, without doing arithmetic on their phone and without silently
ruining the result.

## Problem

Recipe scaling is not multiplication. The failure modes are specific and all of
them are invisible until the cake comes out wrong:

- **Units do not convert without a density.** "1 cup flour" is 125 g, "1 cup
  sugar" is 200 g, "1 cup water" is 237 g. A tool that treats a cup as a fixed
  mass is wrong for almost every ingredient.
- **Fractions are exact or they are wrong.** Doubling 2/3 cup is 4/3 cup, not
  1.3333334 cups; a recipe printed as a decimal is a recipe a cook will
  mis-measure.
- **Some quantities must not scale linearly.** Leavening, salt and spice behave
  non-linearly in practice, and eggs cannot be split into thirds.
- **Pan size changes the result independently of the batch size.** A 9-inch round
  tin and an 8-inch square tin do not hold the same batter, and the difference is
  area, not diameter.
- **Vague quantities are quantities.** "Salt to taste" and "a pinch" must survive
  scaling intact rather than being multiplied into nonsense.

## Solution

A CLI and a library that parse ingredient lines, keep every quantity as an exact
rational, convert across unit families only when a density is known for the
ingredient, scale by factor, target servings or pan geometry, round back to
practical cooking fractions, and flag the parts that do not scale honestly.

## Core workflow

```text
recipe file  ->  parse (quantity, unit, ingredient, note)
             ->  scale (factor | target servings | pan factor)
             ->  convert (density-aware, metric optional)
             ->  round (practical fractions, unit ascent)
             ->  render (text | markdown | html | json)
```

## Must-have features

1. Parse integers, decimals, fractions, mixed numbers, unicode fractions, ranges,
   and vague quantities ("a pinch", "to taste").
2. Exact rational arithmetic throughout; no float in the quantity path.
3. Density-aware volume/mass conversion for a table of common ingredients, with a
   named error when the density is unknown rather than a guess.
4. Scaling by factor, by target servings, or by pan area with an optional depth.
5. Practical rounding: eighths and thirds for volume, sensible gram steps for mass,
   with unit ascent (3 tsp -> 1 tbsp, 1000 g -> 1 kg).
6. Honest flags: eggs split as "1 egg + 1 yolk" style guidance, leavening marked
   as non-linear, salt/spice marked as season-to-taste.
7. Four output formats, all deterministic, all ASCII-safe for Windows consoles.
8. A recipe format that is a plain text file, not a proprietary document.

## Nice-to-have features

- `convert` and `pan` as standalone subcommands.
- Markdown card output suitable for pasting into notes.
- HTML card output with escaped content.

## Stack

Python 3.10+ standard library only (`argparse`, `fractions`, `dataclasses`,
`html`, `json`, `re`), pytest for tests, GitHub Actions for CI.

## Test strategy

- Unit tests for the unit registry and conversions, including the exactness of
  repeated operations.
- Parser tests for every quantity shape the format accepts, plus the shapes it must
  reject with a clear message.
- Scaling tests: factor, servings, rounding boundaries, unit ascent, egg splitting,
  leavening flags, unscalable phrases.
- Pan geometry tests for round, square and rectangular tins, with and without
  depth.
- Render tests, including HTML escaping of an ingredient name containing markup.
- CLI tests asserting exit codes 0, 1 and 2 and deterministic output.

## Demo/result strategy

Ship two example recipes, run the CLI against them for text and JSON output, and
store the observed output under `results/`. `RESULTS.md` quotes what the commands
actually printed on the build machine, including the test count.

## Safety considerations

No network access, no file writes outside the path the user names, no evaluation
of recipe content as code. The parser reads text and the renderers escape it. All
inputs in `examples/` are synthetic.

## Definition of done

Every gate in the pipeline passes: install, tests, CLI demo on both examples,
secret scan clean, README commands verified, results captured, CI green on push,
repository public with the default branch `main`.
