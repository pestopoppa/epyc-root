# AMD AI Lab MVP — local preview

Open `index.html` in a browser to review the static concept. No build step is required.

The package contains:

- `index.html` — landing page and benchmark detail dialog
- `styles.css` — responsive visual system
- `app.js` — detail-dialog interaction
- `data/recipe.json` — first recipe record shape
- `data/catalog.json` — post-BIOS benchmark catalog records
- `postbios.css` — post-BIOS results styling

The page intentionally uses the Gemma 4 / Instinct MI210 result as an **observed** run.
It does not present unmeasured Radeon, Ryzen AI, MI100/MI250, or MI300X combinations as
benchmarks.

The post-BIOS section now reflects the stronger evidence: the 2026-09-21 production CPU
matrix, the MI210 GPU negative control, and the explicit bundle attribution caveat.
