# REPL Session Memory — Maturity Deltas

**Status**: active — D-a, D-b, D-e landed 2026-07-27 (no inference, no instrument-era surface);
D-c rescoped to real-workload measurement (D-c1); D-d unstarted
**Created**: 2026-07-27 (via research intake, operator-approved 2026-07-27)
**Priority**: MEDIUM
**Categories**: agent_architecture, context_management, memory_augmented
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**: [repl-turn-efficiency.md](repl-turn-efficiency.md),
[internal-interaction-lifecycle.md](internal-interaction-lifecycle.md),
[rlm-contested-claims-self-evaluation.md](rlm-contested-claims-self-evaluation.md) (E2 rescoped
2026-07-27 — the code-log measurement lives here as D-c1, on real traffic, not as a synthetic arm
there)

## Objective

Close the specific, verified gaps between our REPL session persistence and fast-rlm's, identified by
Stage-2 dive D1 (2026-07-27) reading both codebases. D-a/D-b/D-e require **no inference** and touch
**no instrument-era surface**.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-901 | fast-rlm REPL memory / resumable sessions (re-review 2026-07-27) | high | adopt_patterns | dive-verified |
| intake-783 | fast-rlm — feature-rich RLM implementation (re-review Jul 2026) | high | adopt_patterns | (pre-lifecycle entry) |

## What we already have — do not re-derive

Dive D1 **overturned** the Stage-1 hypothesis that our checkpointing loses variables silently. It
does not. Existing surface in `epyc-orchestrator`:

- `checkpoint()` / `restore()` — `src/repl_environment/state.py:254,346`
- `SessionPersister` + SQLite store — `src/session/persister.py`, `src/session/sqlite_store.py`
- Non-serializable globals are collected into `skipped_user_globals` (`state.py:320`) **and reported
  to the model**, not just the logger — `src/session/models.py:462-465` renders
  `"Skipped non-serializable variables: ..."` into the resume summary, alongside a restored-variable
  inventory at `models.py:452-461`.
- `variable_lineage` already records role, execution count, timestamp and value type per variable
  (`state.py:313-318`).

**Design boundary, not a gap:** fast-rlm documents *one live query per session directory — concurrent
queries race*. We must not inherit that. We run NUMA-concurrent by design and our session state is
SQLite-backed rather than a single `state.json`. No task is filed for it.

## Tasks

- [x] D-a — **Serialization tier.** ✅ 2026-07-27 — operator-decided (hardened pickle boundary),
      implemented with four independent layers. See *Why D-a needed a decision* and *Security review*
      below.
  - [x] D-a1 — `/security-review` run on the implemented surface ✅ 2026-07-27. Four issues found and
        fixed before landing.
- [ ] D-a2 — **Follow-up: pandas.** DataFrames are deliberately NOT allowlisted in v1 — unpickling
      one pulls in a wide surface of pandas internals (block managers, index constructors) that
      cannot be audited as tightly as the current list. They continue to be reported as unavailable.
      Revisit only with a dedicated review.
- [ ] D-a4 — **Layer-4 `type()` check is literal-dict-only.** `visit_Call` matches
      `type('C', (), {'__reduce__': ...})` when the namespace is a **dict literal**; a variable
      (`d = {...}; type('C', (), d)`) still slips past. Layer 1 holds in that case, so this is
      defense-in-depth only — decide whether to broaden the rule or accept it explicitly.
- [ ] D-a3 — **Guard the allowlist against drift.** `ALLOWED_GLOBALS` must stay inert-data-only;
      `test_no_callable_gadgets_on_the_allowlist` is the regression guard. Any addition needs a
      security pass, especially anything with a nested-deserialization path.
## Why D-a needed a decision, not just effort (verified 2026-07-27)

The original problem statement: `state.py` gates on `_is_json_serializable`, so REPL-defined
functions/classes, numpy arrays, DataFrames and any built index fell into `skipped_user_globals` and
were lost across a resume.

**Why the obvious fix was not obviously safe.** `pickle` is *already* in
`ASTSecurityVisitor.FORBIDDEN_MODULES` (`src/repl_environment/security.py:29`), alongside `os`,
`sys`, `subprocess`, `socket`, `ctypes`. D-a proposes building host-side exactly the capability
the sandbox names as forbidden, over data the sandboxed model authored.

The chain is concrete. `FORBIDDEN_ATTRS` (`security.py:62-83`) does list `__reduce__`,
`__reduce_ex__`, `__getstate__`, `__setstate__` — but `visit_Attribute` only fires on attribute
*access* (`obj.__reduce__`). A class that **defines** `__reduce__` as a method is an
`ast.FunctionDef` inside a `ClassDef`, not an `ast.Attribute`. **Measured: our visitor returns
zero violations** for:

```python
class Index:
    def __init__(self, docs): self.docs = docs
    def __reduce__(self): return (__import__, ("os",))
cached_index = Index([1, 2, 3])
```

Such an object is precisely D-a's motivating case — a built index JSON cannot hold. Under D-a we
would pickle it, and `pickle.loads` at restore invokes the `__reduce__` callable in the
orchestrator process with real builtins, no restricted `__import__`, and no AST visitor. That
converts "model may write restricted Python" into "model may execute arbitrary code in the API
process", and the payload persists in the SQLite session store to re-fire on every resume.

That gap was **latent, not exploitable** before this work — no pickle path existed. Operator
decision 2026-07-27: build it behind a hardened boundary rather than decline it or use a
non-executable format.
- [x] D-b — **Post-restore reconciliation.** ✅ 2026-07-27. `restore()` now reconciles against the
      **live namespace** and returns/stores `{restored, unavailable, claimed, dropped_at_save}`
      (`state.py`), `get_state()` renders a `## Not Restored (do not reference these — rebuild if
      needed)` section so the model is told what is missing rather than only what is present, and the
      executor reports the reconciled count. Tests: `TestRestoreReconciliation` (5 cases) in
      `tests/unit/test_repl_state_extended.py`.
  - [x] D-b1 — **Latent telemetry bug found and fixed.** ✅ 2026-07-27.
        `repl_executor.py` set `restored_globals = len(restore_payload["user_globals"])` — the count
        the checkpoint *claimed*. A name dropped at restore time (builtin collision) was invisible:
        the metric reported success for a variable that never landed. Now sourced from the
        reconciliation, with new `claimed_globals` and `unavailable_globals` fields alongside.
- [ ] D-c — **Code-log resume.** Carry the executed code log into the resume preamble instead of
      prose findings. **Do not design for this yet** (operator, 2026-07-27): the source's own caveat
      says the code dump only stays cheap when follow-ups add a line or two, and "a session where
      every query does heavy multi-step work is the case to watch" — which is our regime. Rather than
      replicate a synthetic n=1 result, measure it on real traffic and let the cost/benefit decide.
  - [ ] D-c1 — **Measure from real workloads, not a synthetic arm.** Instrument resumed sessions to
        record (a) resume-preamble size with the current prose summary, (b) what a code-log preamble
        *would* have cost, and (c) re-derivation work observed after a resume (repeat greps/reads for
        state that was dropped). T3's hard-workflow/tool-use/REPL probe slice is the natural carrier —
        it is already the exploration target for the current era. Zero added inference: this rides
        traffic that is already running.
  - [ ] D-c2 — Decide D-c on D-c1's numbers, or close it if the measured re-derivation cost is
        negligible.
- [ ] D-d — **Curation layer.** An agent-facing annotate/pin call layered over the existing auto-save,
      plus comment-to-variable binding. Lowest priority — we already have `variable_lineage`.
- [x] D-e — **Truncation caps.** ✅ 2026-07-27 (justified, not raised). Extracted to named
      `MAX_RESUME_VARIABLES` / `MAX_RESUME_SKIPPED` constants and made them per-call overridable on
      `format_for_injection()`; `0` means no limit. **Defaults deliberately left at 12/8** — raising
      them changes live prompt content for every resumed session, which is a measured decision, not a
      default flip. Also fixed a real defect while there: the skipped-variable list was truncated to
      8 with **no elision indicator**, so a session with 30 dropped variables silently claimed 8; it
      now reports `(and N more)`.
  - [ ] D-e1 — Decide whether to raise the 12/8 defaults. Same evidence question as D-c
        (prompt-size vs re-derivation cost) — fold into **D-c1's real-workload measurement**, not a
        synthetic arm.

## Open Questions

- Does a pickle tier introduce a deserialization surface we are unwilling to accept for
  model-authored objects, even with a size cap? (D-a is gated on this answer, not on effort.)
- Is source-serialization of REPL-defined functions safe given that restore re-executes definitions?
  fast-rlm's stated invariant is *"saved code is shown, never re-executed"* — with function/class
  definitions the sole exception, justified as deterministic.

## Security review (2026-07-27, on the implemented diff)

Reviewed as a deserialization-of-untrusted-input surface: the pickled objects are authored by
model-written REPL code, and unpickling happens in the orchestrator API process.

**Four layers, each independently verified:**

1. **`find_class` allowlist** (load-bearing). Only explicit `(module, name)` pairs from
   `ALLOWED_GLOBALS` resolve. Verified: a `__reduce__` returning `(__import__, ("os",))` is rejected;
   so is one returning `eval`; so is a hostile object nested inside an object-dtype numpy array; so
   is a correctly-HMAC-signed hostile blob. Model-defined classes live in `__main__`, which is not
   allowlisted, so they cannot be reconstructed at all.
2. **HMAC** over the blob — tampering at rest only. It does not establish content safety, because we
   are the ones pickling model-authored objects. Layer 1 is what makes content safe.
3. **Size cap**, checked from the encoded length before decoding.
4. **AST rule** refusing REPL code that binds a serialization hook.

**Four issues found during review and fixed before landing:**

- **numpy `multiarray.scalar` nested-unpickle gadget.** An object-dtype scalar carries a nested
  pickle in its data buffer that numpy deserializes with plain `pickle.loads` — escaping the
  allowlist entirely. Installed numpy (2.4.4) already refuses it, but that is a *numpy-version-
  dependent* invariant this allowlist must not silently rely on. Now wrapped by
  `_guarded_numpy_scalar`, which rejects object dtypes itself. `scalar` cannot simply be dropped from
  the allowlist — it is required for numpy scalar values such as `np.int64`, though not for arrays.
- **HMAC key race producing an empty key.** The original `O_CREAT|O_EXCL` write published a
  zero-length file before writing; a concurrent worker calling `exists()` in that window read `b""`
  and would have used an *empty, guessable* HMAC key. Now written to a private temp file and
  `os.replace`d atomically, so a reader sees either no file or the complete key.
- **`.strip()` on raw random key bytes.** A 32-byte random key can begin or end with whitespace
  bytes, which `strip()` would silently remove. The key is now hex-encoded on disk, and a short or
  unparseable read is rejected rather than used.
- **Two layer-4 AST bypasses.** The hook could be bound without a `FunctionDef` — via a class-body
  assignment (`__reduce__ = lambda ...`) or `type('C', (), {'__reduce__': ...})`. Both measured as
  passing, both now flagged. Layer 1 held in each case; this was defense-in-depth only.

**Residual risk (tracked, not blocking):**

- The allowlist is a standing invariant, not a one-time check — hence D-a3. Anything added with a
  nested-deserialization path reopens the class of issue found in numpy `scalar`.
- HMAC provenance is meaningful only while the key file stays readable by the orchestrator user
  alone (created 0600). A host-level compromise that can read it can forge envelopes — but such an
  attacker already has the process.
- `dumps()` validates by round-tripping through the allowlist unpickler, so construction happens at
  *save* time as well as restore. Same allowlist, same process, no additional privilege — noted so
  it is not mistaken for a pure-validation step.

## Implementation log

**2026-07-27 — D-a + D-b + D-e landed.** Files changed in `epyc-orchestrator`:

- `src/repl_environment/safe_pickle.py` (**new**) — the hardened boundary: `ALLOWED_GLOBALS`,
  `_AllowlistUnpickler` (with `persistent_load` refused and `_guarded_numpy_scalar`), HMAC signing
  with atomic hex key provisioning, 5,000,000-byte cap, `dumps`/`loads`.
- `src/repl_environment/security.py` — `FORBIDDEN_METHOD_DEFS` plus `visit_FunctionDef`,
  `visit_AsyncFunctionDef`, `visit_Assign`, and a `type(..., {...})` check in `visit_Call`.
- `src/session/{models,protocol,sqlite_store}.py` — `pickled_globals` plumbed through the
  dataclass, restore-protocol normalization, and the SQLite schema (with an additive migration and
  a `_json_col` helper tolerating pre-migration rows).
- `tests/unit/test_safe_pickle.py` (**new**) — 31 cases across all four layers, including the
  adversarial ones.
- `src/repl_environment/state.py` — `restore()` returns a reconciliation dict and stores it on
  `_restore_reconciliation`; reconciles against the live namespace rather than trusting the payload;
  `get_state()` gained the `## Not Restored` section.
- `src/api/routes/chat_pipeline/repl_executor.py` — telemetry sourced from the reconciliation; new
  `claimed_globals` / `unavailable_globals` fields.
- `src/session/models.py` — `MAX_RESUME_VARIABLES` / `MAX_RESUME_SKIPPED` constants,
  `format_for_injection()` overrides, skipped-list elision indicator.
- `tests/unit/test_repl_state_extended.py` — new `TestRestoreReconciliation` (5 cases).
- `tests/unit/test_repl_executor.py` — mock updated to the new `restore()` contract and asserts the
  new telemetry fields.

Verification: 31 passed on the new `test_safe_pickle.py`; **929 passed** on
`-k "session or repl or checkpoint or security or pickle"`. No inference consumed; no instrument-era
surface touched. Nothing committed.

## Notes

Provenance: 2026-07-27 research intake of intake-901, Stage-2 dive D1 against primary source at
pinned SHA `f25f310b` plus a read of our own tree. Full evidence in intake-901 `dive_corrections`.
