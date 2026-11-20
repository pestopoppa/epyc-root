# Supported BFCL single-turn sampling

`bfcl_sample.py` replaces first-ID selection for future supported-frame sampling.
It does not change the fourteen-case coverage rows; the fleet runner now has an explicit supported-frame mode.
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

Remaining CJ-3d work is to prepare content-bound fleet inputs under the contract
below and publish the supported-frame inference row.
No model outputs, quality verdict, or fleet discrimination follow from sampling
or request-construction controls. Previously exposed coverage cases must be
disclosed if they are included in a future measurement.

Run software controls with:

```bash
PYTHONPATH=proposed/cj567 python3 -B -m unittest test_bfcl_sample -v
```

Native capture integration (2026-11-20)

Prepare records outside a grant with `bfcl_sample_capture.py --checkout <checkout>
--selection <selection.json> --output <new-bundle.json>`. This independently
reconstructs the ID-only manifest from immutable git objects, including every
source blob/hash and ranking, then resolves the selected original case/gold
records. The bundle is private input, never a model message. Configure a future
worker with `cohort: supported-frame` and `selection_sha256` equal to this prepared
bundle's SHA-256; place the bundle at `SELECTION.json`. Preserve the config and
bundle hashes in the row's immutable input bindings before publication.
`BoundSample` rejects changed bundle bytes, wrong checker version, reordered or
missing IDs, case/gold ID disagreement and source hashes differing from the
supported-frame corpus lock (`bfcl-supported-frame-lock.json`). Capture checks a frozen per-record copy before creating
the journal. Each identity event includes the sample hash, selection and source
bindings; the native request contains only the official question/tools.
Existing fourteen-case and multi-turn coverage configurations retain their
original selection and semantics. Supported-frame summaries carry category
counts and no automatic pooled quality score.

Prospective first-model diagnostic contract

Question: for the Qwen3.8-27B-Q8_0 native-call instrument at production v10,
what fraction passes the original official AST checker within each of these six
strata, and are failures widespread at the coarse supported-frame scale?
Higher pass fraction is better. This is a descriptive baseline, not a comparison
against published full-BFCL scores or the production REPL path. Record the
explicit result key `bfcl_v3_native_supported_frame_local` when filing; do not
promote this subset into full `bfcl_v3` quality. The worker emits this separate benchmark key and retains `bfcl_v3` only in
`official_checker`; cohort/scope are required qualifiers.

Freeze seed 20261120 and 20 IDs per category before any supported-frame response
is exposed (120 of 1,150). This is a coarse diagnostic aimed at differences of
roughly 30 percentage points; smaller effects cannot support a conclusion here.
For a future descriptive population estimate use weights N_h/1150, never an
unweighted pool. Under the hash-ranking-as-uniform-random-sampling assumption,
a conservative two-sided 95% Hoeffding bound is
sqrt(log(40)/2 * sum_h((N_h/1150)^2/20)) = 0.14282 for that weighted mean.
Simultaneous six-stratum 95% bounds are sqrt(log(240)/40) = 0.37016 each.
These bounds ignore finite-population improvements, exclude systematic instrument
error and model stochasticity, and do not establish power for fleet differences.
A fixed deterministic hash seed is a reproducible sampling convention; these
random-sampling planning bounds are conditional on that assumption.

Before publication, disclose the exact overlap with already selected/exposed
coverage IDs, rather than silently excluding/redrawing them. Freeze model/build,
protocol and config hashes as for existing native coverage. Temperature 0,
seed 20261031, max_tokens 4096 and one attempt per selected ID stay fixed.
Checkpoint every case with the exclusive journal and result file; inspect
technical validity only, with no interim pass-rate decisions. Stop-on-answer
requires all 120 known checker verdicts. Stop-on-futility at the first UNKNOWN,
transport/custody/checker exception, STOP, grant/deadline boundary or lost
residency; preserve partial counts and no success-rate estimate. No retries,
replacement IDs, redraws or continuation after interruption. False checker
verdicts are observations and do not trigger an early stop. No formal adoption
or discrimination gate; formal-gate class remains futility-only. Publish the
row only after its immutable inputs and overlap disclosure are prepared and its
publisher smoke passes; this software integration is not that publication.

The supported-frame lock binds original V3 git blobs separately from the older
coverage lock, which binds released HF corpus bytes. Whole-file identities differ;
no old coverage source binding is rewritten. Supported capture journals the
original git-source hashes, rather than borrowing HF whole-file provenance.
