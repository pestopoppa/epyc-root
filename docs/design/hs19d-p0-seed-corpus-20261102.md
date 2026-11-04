# HS-19d.P0 — illustrative gate and plan seed cases

**Status: author-prepared seed, 2026-11-02; zero inference.** These six synthetic cases are new text written for this document, not extracted from historical task exports or real users. They are proposed labels for review, not observed optimal routes, measured accuracy, a calibrated threshold, or a complete HS-19d.P0 corpus. Each case has a stable ID, exact request text, defined synthetic inputs and a proposed plan shape. Treat the Markdown source at its eventual commit as the initial provenance; before a run, export exact UTF-8 bytes to a machine-readable manifest and pin its digest, source commit, labeling version and any fixture bytes. Missing fixture content or unknown original-run provenance is **unknown**, never silently inferred. Do not substitute historical prompts under these IDs.

Assume the request has no forced mode, existing scouts, or prior dispatch depth, and that all named synthetic paths are within the task scope. These are label-design assumptions, not a claim about live capacity or flag state. Operational bypasses in [dispatch design §5](hs19-stage2-dispatch-20260927.md) take precedence. For plan checks, assume `N_total >= 2` and sufficient scoped access; unknown runtime capacity still defaults to direct. A non-direct label is a hypothesis about usefulness, not an instruction to bypass gates or to run P1–P6, which remain frozen.

## Cases

### HS19-SEED-01 — single-hop question

**Request:** “What is 7 multiplied by 8? Answer with the number.”

**Inputs:** Request only. **Proposed label:** `direct`. **Rationale:** no external evidence or independent work product is required. **Plan expectation:** no child plan. A gate choosing a non-direct mode is a potential false positive under this provisional label.

### HS19-SEED-02 — short localized edit

**Request:** “In `hello.txt`, replace `Hello, Ana` with `Hello, Bea`; report the resulting line.”

**Synthetic input:** `hello.txt` consists of the UTF-8 bytes `Hello, Ana\n` and no other lines. **Proposed label:** `direct`. **Rationale:** one localized operation and check; parallel work would add coordination. **Plan expectation:** no child plan. This case does not authorize access to a real file with that name.

### HS19-SEED-03 — named-file inspection

**Request:** “Read `service.conf` and report the configured port; do not change it.”

**Synthetic input:** `service.conf` consists of the UTF-8 bytes `port=8080\n`. **Proposed label:** `scout`. **Rationale:** a bounded read of a named input is needed before the answer. **Plan expectation:** one or more scoped `read`/`search` targets only; parent reports port 8080. This is a gate example, not proof that scouting is faster than a direct read.

### HS19-SEED-04 — independent document summaries

**Request:** “Summarize the single stated purpose in each of `a.txt` and `b.txt`, then return one labeled sentence per file.”

**Synthetic inputs:** `a.txt` contains `Purpose: collect rainwater.\n`; `b.txt` contains `Purpose: count seeds.\n`. **Proposed label:** `decompose`. **Rationale:** each file can be read and summarized independently. **Plan expectation:** two scoped, self-contained subtasks with no dependency between them; aggregate preserves the file labels. Expected contents are rainwater collection and seed counting. The label is a useful positive control, not a cost claim for this tiny fixture.

### HS19-SEED-05 — independent checks

**Request:** “Check whether the number in `x.txt` is even and whether the word in `y.txt` is lowercase; report each result separately.”

**Synthetic inputs:** `x.txt` contains `12\n`; `y.txt` contains `fern\n`. **Proposed label:** `decompose`. **Rationale:** the checks have disjoint inputs and can run independently. **Plan expectation:** at least two distinct check subtasks, each restricted to its named input, followed by labeled aggregation. Expected results: even = true; lowercase = true. This does not imply a live test runner or shell access.

### HS19-SEED-06 — ambiguous dependency structure

**Request:** “Using only `requirements.txt`, `design.txt`, and `tests.txt`, propose a migration plan that preserves every stated requirement, identifies conflicting constraints, and identifies tests that must change before implementation.”

**Synthetic inputs:** `requirements.txt` contains `Keep old clients working.\nRemove the old endpoint in the first release.\n`; `design.txt` contains `A compatibility proxy is possible.\n`; `tests.txt` contains `One test calls the old endpoint.\n`. **Proposed label:** `decompose_consult`. **Rationale:** the useful split and the compatibility conflict require judgment before independent work can be safely assigned. **Plan expectation:** preserve both requirements and the conflict, avoid assuming the proxy resolves it, and specify dependencies between any synthesis/check subtasks. A valid alternative reviewed label is possible; disagreement stays recorded rather than converted into a measurement.

## Before a corpus can gate evaluation

1. Independently review each proposed label and expected plan, record disagreements and resolution, and add boundary and adversarial controls. Do not derive a label from a model's historical delegation behavior.
2. Add eligible HS-19a and probe-tree cases with pinned sources and privacy review; unavailable native material remains unknown. This document alone does not satisfy the required historical-source portion of P0.
3. Export a versioned manifest and fixture files with stable IDs, explicit scope, input digests, pre-run labels and validation controls for duplicate IDs, missing bytes, invalid labels and broken dependencies. Freeze the manifest before any evaluation.
4. The protocol annex, belief write-side, capacity and running-window requirements remain separate. No inference, dispatch, model-quality claim or threshold calibration is authorized by these seeds.
