"""Renderers for a scaled recipe.

Four formats, all deterministic and all ASCII-safe so that a Windows console with
a legacy code page prints the same characters as a Linux terminal. Ingredient
text is escaped in HTML output because a recipe file is untrusted text.
"""

from __future__ import annotations

import html

from .scale import ScaledRecipe, format_quantity

__all__ = ["render_text", "render_markdown", "render_html"]


def _meta(scaled: ScaledRecipe) -> str:
    """The scaling line, without the title."""

    parts = [f"factor {format_quantity(scaled.factor)}x"]
    if scaled.source_servings is not None and scaled.target_servings is not None:
        parts.append(
            f"servings {format_quantity(scaled.source_servings)} -> {format_quantity(scaled.target_servings)}"
        )
    return ", ".join(parts)


def _header(scaled: ScaledRecipe) -> str:
    return f"{scaled.title}  ({_meta(scaled)})"


def _amount(item) -> str:
    if item.unscalable:
        return "as written"
    if item.unit_text:
        return f"{item.quantity_text} {item.unit_text}"
    return item.quantity_text


def render_text(scaled: ScaledRecipe) -> str:
    """Aligned plain-text card, suitable for a terminal or a text file."""

    rows = [(item.name, _amount(item), item.grams or "", item.package or "") for item in scaled.items]
    name_width = max([len("ingredient")] + [len(row[0]) for row in rows])
    amount_width = max([len("amount")] + [len(row[1]) for row in rows])

    lines = [_header(scaled), ""]
    lines.append(f"{'ingredient'.ljust(name_width)}  {'amount'.ljust(amount_width)}  grams")
    lines.append(f"{'-' * name_width}  {'-' * amount_width}  {'-' * 5}")
    for name, amount, grams, package in rows:
        suffix = f"  [{package}]" if package else ""
        lines.append(f"{name.ljust(name_width)}  {amount.ljust(amount_width)}  {grams}{suffix}")

    flagged = [item for item in scaled.items if item.flags]
    if flagged:
        lines.append("")
        lines.append("notes")
        for item in flagged:
            for flag in item.flags:
                lines.append(f"  - {item.name}: {flag}")

    if scaled.notes:
        lines.append("")
        lines.append("scaling")
        for note in scaled.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def render_markdown(scaled: ScaledRecipe) -> str:
    """Markdown card with a table, for pasting into notes or a pull request."""

    lines = [f"### {scaled.title}", "", f"*{_meta(scaled)}*", ""]
    lines.append("| Ingredient | Amount | Grams | Note |")
    lines.append("|---|---|---|---|")
    for item in scaled.items:
        amount = _amount(item).replace("|", "\\|")
        name = item.name.replace("|", "\\|")
        note = "; ".join(filter(None, [item.note, item.package, *item.flags])).replace("|", "\\|")
        lines.append(f"| {name} | {amount} | {item.grams or ''} | {note} |")
    if scaled.notes:
        lines.append("")
        lines.extend(f"- {note}" for note in scaled.notes)
    return "\n".join(lines)


def render_html(scaled: ScaledRecipe) -> str:
    """Self-contained HTML card. All recipe text is escaped."""

    rows = []
    for item in scaled.items:
        note = "; ".join(filter(None, [item.note, item.package, *item.flags]))
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td>{html.escape(_amount(item))}</td>"
            f"<td>{html.escape(item.grams or '')}</td>"
            f"<td>{html.escape(note)}</td>"
            "</tr>"
        )
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in scaled.notes)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(scaled.title)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 46rem; padding: 0 1rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid #ddd; }}
  caption {{ text-align: left; font-weight: 600; padding-bottom: 0.6rem; }}
  .meta {{ color: #555; }}
</style>
</head>
<body>
<table>
  <caption>{html.escape(scaled.title)}</caption>
  <tfoot><tr><td colspan="4" class="meta">{html.escape(_header(scaled))}</td></tr></tfoot>
  <thead><tr><th>Ingredient</th><th>Amount</th><th>Grams</th><th>Note</th></tr></thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
<ul>{notes}</ul>
</body>
</html>
"""
