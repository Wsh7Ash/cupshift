"""cupshift: scale recipes with exact unit algebra.

The public entry points live in the submodules and are imported by name rather
than re-exported here, so that ``import cupshift`` stays cheap:

    from cupshift.parse import parse_recipe_file
    from cupshift.scale import scale_recipe
    from cupshift.units import convert, density_for, lookup
    from cupshift.pan import parse_pan, pan_factor
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
