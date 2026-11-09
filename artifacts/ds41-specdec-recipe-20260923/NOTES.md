# DS41 C2b — DSpark speculative decoding in the AutoKernel recipe layer

**PREPARE ONLY.** Patches in this directory apply to `epyc-inference-research` at
`origin/main` = `58b115ed` ("architect_critic: record the CONVERGED general-suite
quality"). Nothing was committed, no loop ran, no inference ran, no process was started
or stopped, `/mnt/raid0/llm/llama.cpp` was never touched.

Apply order: `0001-dspark-recipe.patch`, then `0002-tests.patch`.

## The blocker, as found

`scripts/kernel_rnd/autokernel/loop/resolved_recipe.py:29` (pristine)

    SPECULATION_TYPES = frozenset({"none", "draft-dflash", "draft-mtp"})

is the **only** speculation allowlist in the repo — verified by `grep -rn 'draft-dflash'
scripts/ artifacts/`: every other hit is a docstring, a standalone bench script under
`scripts/benchmark/`, or a shipped recipe JSON. So a recipe could not say
`draft-dspark`, the prepared campaign recipe was forced to `spec_decode: {"type":
"none"}`, and the campaign would have optimised the no-drafter surface.

Everything *around* the enum was already general: `serving.Recipe.server_argv`
(`serving.py:520-524` pristine) emits `-md/-ngld/--spec-type/--spec-draft-n-max` for any
non-`none` type, and the drafter digest was already in the resolved artifact set. The
enum was the whole gate.

## What changed

### 1. `draft-dspark` is expressible — `resolved_recipe.py:27-38`

`SPECULATION_TYPES` gains `draft-dspark`, plus three small companion sets that say *why*
this type is special rather than special-casing a string in five places:
`SINGLE_SLOT_SPECULATION_TYPES`, `EXTERNAL_DRAFTER_SPECULATION_TYPES`,
`EXACTNESS_REQUIRED_SPECULATION_TYPES`. All three are exported.

No change was needed in `serving.server_argv` — it was already general — so the argv for
our operating point falls out of the existing construction. `planned_serving.py:425`
already carries `drafter_digest` into the arm identity; nothing there needed touching.

### 2. `--parallel 1` REFUSES, it does not override — `resolved_recipe.py:_validate_template`

A `draft-dspark` recipe with `np != 1` raises `ResolutionError`
("requires --parallel 1 … Refusing rather than overriding np"). This is the
`-tb != -t` idiom at `resolved_recipe.py:600` (pristine), one level up: a refusal, not a
rewrite, because a silently rewritten `np` is a different measured condition wearing this
recipe's hash, and every serving floor is keyed by `recipe_hash`
(`serving.py:404-421`).

It is rechecked **from argv** in `_validate_resolved_consistency`, independently of the
template (`-np`/`--parallel` are the same knob, and `-np` is what the server sees), along
with "dspark without `-md`".

### 3. The env problem — `LLAMA_SPEC_EXACT` with a real witness

`unified_planner.py:458-459` is an equality assertion (`{k: v for k, v in
recipe.launch_env if k != "LD_LIBRARY_PATH"} == dict(execution.env)`), and
`resolve_recipe` (`resolved_recipe.py:1291-1294` pristine) refuses any recipe env key not
in `EnvironmentPolicy.measurement_keys`, which in turn requires a witness kind per key
(`EnvironmentPolicy.from_dict`, `resolved_recipe.py:163-166`). So the key had to be added
*with* a witness or planning refuses. It is measurement-relevant in the strongest sense:
it selects the **verification path**, so it changes throughput *and* output exactness.

The existing witness kinds could not carry it. `recipe_readback` reads
`/proc/<pid>/status` fields (`serving.verify_env_readback`), and `LLAMA_SPEC_EXACT` is not
a status field. `runtime_set` has **no sampler at all** — `_witness_reports` stamps it
`status="unknown", reason="witness_sampler_not_implemented"` and `_capability` does not
refuse on it, so declaring the key under `runtime_set` would have been the documentation-
wearing-a-guard's-clothes failure the sibling DSO effort's NOTES warns about.

So this patch adds a **fourth witness kind, `process_environ`**, with an actual sampler:

* `serving.verify_process_environ(recipe, pid, expectations=…)` reads
  `/proc/<pid>/environ`, splits on NUL, and refuses in **both** directions — a value that
  differs *and* a variable that is present when the recipe unset it — plus an unreadable
  `/proc` (`EnvReadbackFailed`). Same fail-closed shape as `verify_env_readback`.
* `_witness_reports` **derives** the expectation from the recipe rather than taking a
  second hand-written declaration: `("environ:LLAMA_SPEC_EXACT", <value>)`, or
  `serving.UNSET` when the recipe explicitly unsets it. A key the recipe neither sets nor
  unsets is *inherited*, so its value is not knowable offline; the witness stays
  `unknown` with `reason="process_environ_not_declared"` rather than inventing an
  expectation that would pass against whatever the parent happened to carry.
* `_capability` refuses on an unknown `process_environ` witness
  (`process_environ_witness_missing`), and separately refuses a greedy dspark recipe that
  has no *declared* `process_environ` witness for `LLAMA_SPEC_EXACT`
  (`spec_exactness_witness_missing`) — so a policy that names the key under `runtime_set`
  yields `supported=False`, not a green recipe with an unproven knob.
* `_validate_resolved_consistency` cross-checks the declared witness against the frozen
  launch (`field == "environ:<KEY>"`, `expected ==` the relevant value or `UNSET`, and the
  value is actually in `launch_env`).

**WHAT THE WITNESS RECORDS, precisely** (also in the `verify_process_environ` docstring):
that the variable was **delivered to the process at exec** with that value, or was absent.
It does **not** record that the server read it, and it is not a claim about the
verification path the kernel then took. The complementary half — that the knob is
compiled into the executing artifact at all (`strings <lib> | grep LLAMA_SPEC_EXACT`; a
null from a knob that is not in the binary is not evidence about the knob) — belongs with
build provenance and is **not** duplicated here; see *Not closed* (3).

**The refusal that would have caught today's failure**: `_validate_exactness` raises
`ResolutionError` when a greedy (`temperature == 0.0` **or** `top_k == 1`) dspark recipe
does not declare `LLAMA_SPEC_EXACT`. Message names the consequence: the SERIAL
verification path, 1 token per target decode, never above 1x. Absence is a refusal, not a
fallback. Also refused: a value outside `serving.SPEC_EXACT_MODES`, and declaring the
variable on a `spec_decode.type == "none"` recipe (claiming a condition the launch does
not have). A *non-greedy* dspark recipe (the block-3 / temp-0.7 point) does **not**
require it — the path is not selectable there, and a blanket rule would have been a
guard that refuses its own idiom.

### 4. The drafter is part of the identity — mostly ALREADY TRUE, one gap closed

Found and verified rather than added:

* **Path** is in `recipe_hash` — `to_dict()` includes `spec_decode`
  (`serving.py:390`), and the hash covers `to_dict()` (`serving.py:420-422`).
* **Digest** is in the resolved artifact set (`_artifact_set`,
  `resolved_recipe.py:854-870`), in `snapshot_digest` via `_snapshot_dict`
  (`resolved_recipe.py:330`), and in `execution_digest` via `_normalized_execution_dict`
  — both as the `-md` argv normalisation `<drafter:{sha256}>`
  (`resolved_recipe.py:346-347`) and as `artifacts.drafter`
  (`resolved_recipe.py:364`).
* Deliberate and correct asymmetry, asserted in the tests: moving the drafter on disk
  changes `template_hash` and `snapshot_digest` but **not** `execution_digest`
  (relocation-invariant by construction); changing the drafter **bytes** changes
  `execution_digest` with the template hash unmoved. A recipe hash alone cannot see a
  swapped drafter; the execution digest can.
* Gap closed: `ResolvedRecipe.validate_launch` now refuses a drafter path that is
  missing, a directory, or unreadable. Resolution is offline by contract ("performs no
  hashing, building, downloading"), so `validate_launch` is the only place the pinned path
  can be coupled to a file that exists. It checks presence and readability, **not**
  content.

**Composition with `/mnt/raid0/llm/tmp/ds41-dso-identity/`** (read before writing this):
that effort deliberately leaves `validate_launch` untouched (its *Not closed* item 3:
"`validate_launch` still does not hash the executable before `Popen`"). It adds
`loop/build_provenance.py` and touches `campaign_cli.py`, `unified_driver.py`,
`measurement_capture.py`, `native_capture_control.py`, `bench.py`, `cpu_profile.py`,
`actors.py`. **Zero file overlap with this patch** except `resolved_recipe.py`, which that
effort does not modify. The two compose: when DSO identity lands, hashing the drafter at
launch is a one-line extension of the block added here, using `build_provenance`'s digest
helper rather than a second spelling. Nothing here depends on it landing.

## What now REFUSES that did not

| Refusal | Where | Class |
|---|---|---|
| `draft-dspark` at `np != 1` (template) | `_validate_template` | `ResolutionError` |
| `draft-dspark` at `--parallel != 1` (argv, independent recheck) | `_validate_resolved_consistency` | `ResolutionError` |
| `draft-dspark` with `-md` absent from resolved argv | `_validate_resolved_consistency` | `ResolutionError` |
| `draft-dspark` with no `drafter` (never self-drafting) | `_validate_template` | `ResolutionError` |
| greedy `draft-dspark` with `LLAMA_SPEC_EXACT` unset or explicitly unset | `_validate_exactness` | `ResolutionError` |
| `LLAMA_SPEC_EXACT` set to an unknown verification path | `_validate_exactness` | `ResolutionError` |
| `LLAMA_SPEC_EXACT` declared on a `type: none` recipe | `_validate_exactness` | `ResolutionError` |
| greedy `draft-dspark` whose policy cannot *witness* the exactness key | `_capability` | `spec_exactness_witness_missing` → `supported=False` |
| any `process_environ` measurement key the recipe does not own | `_capability` | `process_environ_witness_missing` → `supported=False` |
| a `process_environ` witness whose expectation differs from the frozen launch | `_validate_resolved_consistency` | `ResolutionError` |
| a launched process whose `/proc/<pid>/environ` differs from the recipe, in either direction | `serving.verify_process_environ` | `EnvReadbackFailed` |
| a missing / unreadable / directory drafter at launch | `ResolvedRecipe.validate_launch` | `ResolutionError` |

One guard was **narrowed**, deliberately: the "declared capability witness is absent from
readback checks" check now applies only to `recipe_readback` witnesses. It compares
against `readback_expectations`, which is the `/proc/<pid>/status` declaration set derived
from `Recipe.env_readback`; a `process_environ` witness is checked against a different
surface and is cross-checked against the frozen launch instead (stronger, since its
expectation is derived, not declared). No `recipe_readback` behaviour changed.

## The argv and env for our operating point

Drafter `/mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash-DSpark.gguf` (9.32 GiB,
arch `deepseek41-dspark`), block 2, greedy, CPU, acceptance 51.6%, 17.85 t/s median vs an
11.43 t/s no-drafter control. Asserted element-for-element in
`test_operating_point_resolves_and_emits_exactly_the_measured_argv_and_env`.

    /build/bin/llama-server -m <target.gguf> -np 1 -c 4096 -t 96 -tb 96 -b 2048 -ub 512
      -ctk f16 -ctv f16 --device none -ngl 0 -fa on --host 127.0.0.1 --port 18317
      --metrics --slots -md <DeepSeek-V4.1-Flash-DSpark.gguf> -ngld 0
      --spec-type draft-dspark --spec-draft-n-max 2 --no-kv-unified --device-draft none

    env: LD_LIBRARY_PATH=/build/bin  LLAMA_SPEC_EXACT=batched-greedy-inexact

`--parallel 1` is satisfied by `-np 1` (`_STRUCTURED_FLAGS` already treats `-np` and
`--parallel` as the same knob, `resolved_recipe.py:32`); no second flag is emitted.
`-ngld 0` + `--device-draft none` is what the existing `_capability` CPU branch requires
of an external draft on a CPU main model (`mixed_cpu_gpu_draft_unsupported`), so the CPU
operating point needs `extra_flags=("--device-draft", "none")`. Block 5 is recorded as
REJECTED (break-even) and needs no encoding — `draft_n_max` is in `execution_digest`, so
blocks 2/3/5 are three distinct measurements, asserted in
`test_block_size_is_part_of_the_identity`.

## Tests

`0002-tests.patch` adds `loop/test_specdec_dspark.py`, **23 tests, all passing**, and
changes no existing test. Coverage maps to the task's four requirements: exact argv+env
for the operating point; np>1 refuses (with a `draft-dflash` at np=4 control proving the
refusal is about dspark and not about np); missing / unreadable / directory drafter
refuses (with a present-and-readable control in the same test, so the refusal is not
vacuous); and the exactness env required for the greedy variant, by both greedy
spellings, with the temp-0.7 block-3 recipe as the control that must NOT require it.

Suites run on the patched tree, all green:
`test_resolved_recipe test_serving test_selfdraft_recipe test_recipe_env
test_cpu_serving_recipe` (113 passed, 20 subtests), `test_planned_serving
test_serving_preparation test_serving_floor_identity test_unified_planner
test_unified_worker test_campaign` (161 passed, 3 subtests), plus the full set of loop
test modules that import `serving` or `resolved_recipe` (see *Validation* below).

## Not closed

1. **`allowed_inherit_keys` + `process_environ` is an unknown witness, by design.** If a
   campaign ever wants `LLAMA_SPEC_EXACT` inherited from the parent rather than set by the
   recipe, the witness cannot derive its expectation offline and the recipe becomes
   unsupported. That is the correct reading — the recipe would not own the value — but it
   means the only supported way to run dspark greedy is for the recipe to set the variable
   itself. Stated rather than worked around.
2. **The witness proves delivery, not effect.** `/proc/<pid>/environ` shows the exec-time
   environment. Proving the server *took* the batched path needs a server-side readback
   (a `/props` field or a startup log line) that this fork does not currently expose in a
   form I could verify without running inference — which this task forbids. If such a
   field exists, it is one `recipe_readback`-shaped addition on top of what is here, and
   the two witnesses are complementary, not redundant.
3. **No `strings <binary> | grep LLAMA_SPEC_EXACT` gate.** The knob-not-in-the-binary
   failure class (INF-70 C9) is real for this knob too, but the right home is
   `build_provenance.py` from the sibling DSO-identity patch, which already does a bounded
   byte scan of the artifact for marker strings. Adding a second scanner here would be two
   spellings of one check. Follow-up: extend that module's `MARKERS` with the spec-exact
   knob once it lands.
4. **`validate_launch` still does not hash the drafter**, only stats it. Same reason as
   the sibling effort's item 3 — hashing at launch touches the path where an error costs a
   run, and it wants the DSO-identity machinery rather than a local hash call.
5. **No campaign recipe JSON is written here.** This patch makes the surface expressible;
   authoring `artifacts/serving-recipes/<name>.json` for the DS41 campaign, and the
   matching `EnvironmentPolicy` with the `process_environ` witness, is the campaign
   owner's write. The exact shape is in `test_specdec_dspark._recipe` / `_policy` and can
   be lifted verbatim.

## Validation performed (2026-09-23, prepare-only)

* Scratch clone at `origin/main` (`58b115ed`) in `scratch/`; both patches
  `git apply --check` clean against a pristine clone, individually and as a series.
* Patched tree: the two blast-radius suites above, plus every loop test module that
  imports `serving` or `resolved_recipe` (64 modules on the patched tree, 63 on pristine
  -- the difference is the new test file). Run with `-p no:randomly` on both sides:

      patched   32 failed, 908 passed, 1 xfailed, 27 errors, 23 subtests
      pristine  32 failed, 885 passed, 1 xfailed, 27 errors, 23 subtests

  The two failure sets are **identical, name for name**:
  `comm -23 failed-patched.txt failed-pristine.txt` and its mirror are both EMPTY (59
  FAILED/ERROR node ids each side, `failed-patched.txt` / `failed-pristine.txt` in this
  directory, raw logs in `suite-dependents.txt` / `suite-pristine.txt`). So: zero
  regressions, and the +23 passed are exactly the new tests. The autokernel tree is not
  green on pristine either, which the sibling DSO effort observed independently -- those
  failures are pre-existing and out of scope here.
* No commit, no push, no loop run, no inference, no server launched, no process signalled.
