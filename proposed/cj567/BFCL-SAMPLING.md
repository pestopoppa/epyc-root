# Supported BFCL single-turn sampling

`bfcl_sample.py` replaces first-ID selection for future supported-frame sampling.
It does not change the fourteen-case coverage rows or the fleet runner.
It reads case and gold files directly from git objects at the bridge's pinned
official V3 commit, checks full case/gold ID equality and supported input shapes,
and records all twelve source blobs and SHA-256 hashes. Local working-file edits
cannot change the selected frame. Output contains IDs and bindings only.

Before publishing inference, run outside a grant:

```bash
PYTHONPATH=proposed/cj567 python3 -B proposed/cj567/bfcl_sample.py \
  --checkout /path/to/pinned-gorilla-checkout \
  --per-category 20 --seed 20261120 --output /scratch/selection.json
```

The integer size and seed are explicit inputs. Within each category the tool
ranks IDs by SHA-256 of compact JSON `[seed,category,id]` and takes the lowest
priorities without replacement. Input ordering and gold values cannot influence
selection. It refuses duplicate IDs, missing categories, oversampling, malformed
single-turn cases, missing gold, and output overwrite. It never downloads data.

The frame contains simple (400), multiple (200), parallel (200),
parallel_multiple (200), Java (100), and JavaScript (50): 1,150 cases total.
The twenty-per-category example is a software validation fixture, not a claim
of sufficient statistical power or an approved measurement design. It samples
different fractions of these categories. Report per-category outcomes; an
unweighted pooled score does not estimate the frame's population success rate.
SQL, irrelevance, chatable, REST, executable, live and multi-turn categories
are outside this frame, so it cannot yield a full `bfcl_v3` benchmark score.

Remaining CJ-3d work is to fix a prospective measurement question and sample
size/error and stopping contract, integrate these IDs with immutable original
records and the native capture runner, and publish the resulting inference row.
No model outputs, quality verdict, or fleet discrimination follow from sampling
or request-construction controls. Previously exposed coverage cases must be
disclosed if they are included in a future measurement.

Run software controls with:

```bash
PYTHONPATH=proposed/cj567 python3 -B -m unittest test_bfcl_sample -v
```
