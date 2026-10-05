# Social graphics tooling
- `render.py` renders 1080x1080 ForeSite graphics from a JSON spec (see docstring).
- `publish.sh spec.json` renders into `weekly/<Monday>/`, commits, pushes and prints raw URLs pinned to the commit SHA (use these in Metricool; they work immediately, unlike `/main/` links which are cached for a few minutes).
- Fonts: Plus Jakarta Sans and Inter (SIL Open Font Licence, see fonts/OFL.txt). Logo: brand/logo-dark-bg.png.
