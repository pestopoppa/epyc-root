# The 13 unscoreable rows are real — and they are the small half of the defect

**Date**: 2026-08-12 · **Auditor**: `mainD` · **Lane**: `none` (read-only over the pool, the
upstream HF snapshots and the adapter source; no inference, no servers, no compute) · **Source
row**: `handoffs/active/autopilot-continuous-optimization.md` — *"14 residual unscoreable rows are
broken DATA, not scorer bugs — `livecodebench` 11 …, `cruxeval` 1 …, `mode_advantage_hard` 1.
Either regenerate their oracles or retire the rows."*

---

## Verdict table

| Claim in the row | Status |
|---|---|
| 14 residual unscoreable rows | **CORRECTED → 13** (the row's own enumeration also sums to 13) |
| `livecodebench` 11 with comment-only `test_code` | **CONFIRMED exactly — 11** |
| `cruxeval` 1 "has no ground truth anywhere" | **REFUTED** — ground truth exists upstream and is faithfully carried; it is the **empty string**, because the function takes no arguments |
| `mode_advantage_hard` 1 | **CONFIRMED — 1**, and it is hand-authored, in git, and repairable |
| "broken DATA, not scorer bugs" | **REFUTED** — the 11 are produced by a **code** defect in the LeetCode adapter, still on `main` |
| These 13 are the residue | **REFUTED — the material finding is elsewhere: the other 2,349 `livecodebench` rows score, and their oracle is `"def "`.** |

---

## 0. What was measured, and against what

Pool actually consumed by the eval tower (`scripts/autopilot/eval_tower.py:3579-3583`):

```
/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl
size 1,350,221,880   mtime 2026-08-04 07:02:15Z
1 __pool_metadata__ line + 79,479 question rows
gitignored (.gitignore:89) — so it is NOT verifiable against git; provenance is mtime + its own metadata header
```

Predicate applied: a byte-for-byte transcription of `_is_scoreable_question` and its helpers
(`_has_code_execution_oracle`, `_has_executable_assertion`, `_has_unittest_case`,
`_is_rubric_scored_question`, `_EXPECTED_FREE_SCORERS`) from
`/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py:656-732`, run over all 79,479
rows. `__pool_metadata__` excluded.

**Result: 13 unscoreable rows, in exactly the three suites named.**

```
livecodebench          11 / 2360
cruxeval                1 / 1600
mode_advantage_hard     1 /   60
------------------------------------
TOTAL                  13 / 79479
```

**On the missing 14th.** 11 + 1 + 1 = 13; the row's headline and its own enumeration already
disagree. The most likely origin is that the counting pass included the `__pool_metadata__` header
line as a row — it carries no `expected` and no `scoring_method`, so it is unscoreable under
`_is_scoreable_question` taken alone (in the real tower it is rejected one step earlier, by
`_question_validation_errors`, for missing required fields, and would be booked under a different
drop reason). **I could not prove this**: the 2026-08-04 counting script was not persisted and the
pool has not been regenerated since, so there is no way to re-run what produced the 14.

---

## 1. `livecodebench` — 11 unscoreable, 2,349 scoring on a vacuous oracle

### 1a. The 11 are a code defect, not damaged data

`epyc-orchestrator/scripts/benchmark/dataset_adapter_modules/coding.py:421-432`
(`LiveCodeBenchAdapter._row_to_prompt`), introduced `2a7b2142`, 2026-05-22:

```python
test_code = f"# Test cases for {fn_name}\n"
for inp, out in test_cases:
    test_code += f"# assert {fn_name}({inp}) == {out}\n"
...
scoring_method = "code_execution" if test_code else "substring"
```

Every line the adapter emits is prefixed `#`. It then labels the row `code_execution`. So the
adapter **cannot ever** emit an executable oracle on this path: a row that gets test cases becomes
a `code_execution` row whose test body is 100% comments, which is precisely what
`_has_executable_assertion` rejects. Measured: **0 of 2,360 `livecodebench` rows contain an
uncommented `assert`, and 0 carry an `entry_point`.**

Uncommenting the `#` would not fix it. `_extract_test_cases` scrapes `Input:`/`Output:` pairs out
of the problem's **prose** with a regex, and on these 11 it captured English, not values:

```
# assert __init__(/) == as a list of
# assert reverse_bits(and) == will be given as a signed integer type. …
# assert minCost(/) == way as normal binary trees where each node is represented as a pair of
```

The extraction is the defect; the comment prefix merely hides it as a silent drop instead of a
1,000-row systematic failure. **Removing the `#` without fixing the extraction would convert 11
dropped rows into 11 always-fail rows** — the same trap the 2026-08-04 note flagged for the
scorer-before-validator ordering.

### 1b. The other 2,349 are worse, because they score

The `else` branch of the same block:

```python
scoring_config["case_sensitive"] = True
scoring_config["substring"] = "def "
...
"expected": "def ",  # At minimum, expect a function
```

Measured over the pool:

```
livecodebench rows                       2360
distinct `expected` values                  1     ("def ")
scored by `substring`                    2349
scored by `code_execution` (the broken 11)  11
```

**The oracle for 2,349 live rows is: "does the output contain the four characters `def `".** Every
syntactically plausible Python answer passes; a wrong answer passes; `def f(): pass` passes. It
cannot separate a correct solution from an incorrect one, and it is *identical on every question in
the suite* — an oracle constant across a suite carries zero per-question information by
construction.

These rows are live in both core pools right now:

```
core_v2.jsonl                       leetcode_dungeon-game                                   substring "def "
core_v2.jsonl                       leetcode_flip-equivalent-binary-trees                   substring "def "
core_v2_ledger_20260703_min5.jsonl  leetcode_making-file-names-unique                       substring "def "
core_v2_ledger_20260703_min5.jsonl  leetcode_substring-with-concatenation-of-all-words      substring "def "
core_v2_ledger_20260703_min5.jsonl  leetcode_verifying-an-alien-dictionary                  substring "def "
```

This is the same class as the debugbench finding
(`artifacts/audit/debugbench-oracle-vacuity-20260812.md`), reached by a different route, and it
confirms that audit's §4 prediction that the ingestion path has more than one defect.

### 1c. The shipped vacuity guard does not catch it — stated plainly

`core_v2_select.vacuous_rows` (`cc81d0ff`) asks *"is `expected` already present in the model's
input?"*. Measured on these rows: **`"def "` appears in the prompt of only 16 of 2,349**, and at
length 4 it is below `_STRUCTURAL_MIN = 40`, so all 16 would be filed as *incidental*. **The guard
reports nothing actionable for livecodebench.** It is not wrong — it tests a different, real
property — but this family (a *constant, trivially-satisfiable* oracle) slips past it. §5 proposes
the complementary test and it is implemented alongside this audit.

### 1d. Can the oracle be regenerated?

Upstream is cached locally:
`/mnt/raid0/llm/hf-home/hub/datasets--greengerong--leetcode/snapshots/00f2d466…/leetcode-train.jsonl`,
2,360 rows — an exact 1:1 with our suite. Fields:

```
id, slug, title, difficulty, content, java, c++, python, javascript
```

**There are no test cases upstream.** There is prose (`content`) and a reference solution per
language. So a correct `code_execution` oracle cannot be *transcribed* from the source — it would
have to be *manufactured*, either by parsing LeetCode's example blocks reliably (which is the thing
that just failed) or by differential execution against the upstream `python` reference on generated
inputs. That is a real engineering project, not a data patch.

---

## 2. `cruxeval` — 1 row, and the claim about it is wrong

`cruxeval_input_0135`, `scoring_method: exact_match`, `expected: ""`.

Upstream, `/mnt/raid0/llm/hf-home/hub/datasets--cruxeval-org--cruxeval/snapshots/b96af045…/test.jsonl`,
row index 135 (`id: sample_135`):

```
code   = "def f():\n    d = {…}\n    return list(d.keys())"
input  = ''                              <-- the ground truth, verbatim
output = "['Russia', 'Kazakhstan']"
```

**Exactly 1 of 800 upstream rows has an empty `input`; 0 have an empty `output`.** Our pool carries
that empty string faithfully. So the row is **not** "missing ground truth anywhere" — the ground
truth is present, correct, and empty, because the function `f()` takes no arguments.

The defect is the **question**, not the oracle. The `cruxeval` input-prediction task asks *"determine
what input was provided"*; for a zero-argument function the question is ill-posed, and the only
correct response is to emit `<answer></answer>` with nothing inside. Upstream ships this row for the
output-prediction direction (`cruxeval_output_0135`, `expected: "['Russia', 'Kazakhstan']"`, which
scores fine); it is our adapter that also materialises the input direction for it.

---

## 3. `mode_advantage_hard` — 1 row, hand-authored, in git, repairable

`ma_hard_code_001`. Source of truth is **not** generated —
`epyc-inference-research/benchmarks/prompts/debug/mode_advantage_hard.yaml:288-328` (tracked, and
clean in the working tree at the time of this audit). Two independent defects:

**(a) The oracle asserts nothing.** `test_code` wires stdin and then stops:

```python
import sys
from io import StringIO
# Test case 1
test_input = "4 5 2\n1 2 1\n1 3 5\n2 3 1\n2 4 10\n3 4 1\n"
sys.stdin = StringIO(test_input)
# The solution should read from stdin and print to stdout
```

No `assert`, no stdout capture, no comparison. It is scaffolding that was never finished.

**(b) The prompt ships the author's unresolved self-correction**, so the row states two different
answers and then a third time reverses:

```
Output: 3
(Path: 1→2→3→4 with total weight 3, using 3 edges... wait, that's 3 edges.
 With K=2: 1→3→4 = 6, 1→2→4 = 11. Answer should be 6)

Actually output: 6
```

A model reading this is being told the answer is 3, then that it is 6. Even with a working oracle,
the prompt is defective. The correct answer for the stated instance (shortest 1→N using at most
K=2 edges) is **6** (1→3→4).

---

## 4. Decision per row

Format: `id — DECISION — reason`.

### RETIRE (12)

| # | id | reason |
|---|---|---|
| 1 | `leetcode_copy-list-with-random-pointer` | oracle is scraped English, not a test; no upstream test cases to regenerate from |
| 2 | `leetcode_insertion-sort-list` | ditto |
| 3 | `leetcode_reverse-bits` | ditto |
| 4 | `leetcode_serialize-and-deserialize-binary-tree` | ditto |
| 5 | `leetcode_logical-or-of-two-binary-grids-represented-as-quad-trees` | ditto |
| 6 | `leetcode_tag-validator` | ditto |
| 7 | `leetcode_fraction-addition-and-subtraction` | ditto |
| 8 | `leetcode_construct-string-from-binary-tree` | ditto |
| 9 | `leetcode_design-search-autocomplete-system` | ditto |
| 10 | `leetcode_clone-binary-tree-with-random-pointer` | ditto |
| 11 | `leetcode_add-two-polynomials-represented-as-linked-lists` | ditto |
| 12 | `cruxeval_input_0135` | the oracle is already correct; the **question** is degenerate (zero-argument function, so the only right answer is empty). Nothing to regenerate. 1 row of 1,600 = 0.06% of the suite. The output-direction twin `cruxeval_output_0135` is unaffected and stays. |

Retiring 1-11 is **not** a way to make `livecodebench` sound — see §5.1. It removes 11 silent drops;
it leaves 2,349 vacuous passes.

### REGENERATE (1)

| # | id | reason |
|---|---|---|
| 13 | `ma_hard_code_001` | Hand-authored YAML, tracked in git, one problem, one test case. Regeneration is: (i) rewrite the prompt to state the instance and the single answer `6`, deleting the self-correction; (ii) replace `test_code` with a real oracle that captures stdout and asserts `== "6"`. Cost is minutes, and unlike the LeetCode rows there is no missing upstream to reconstruct. **Both** defects must be fixed together — repairing only the oracle leaves a prompt that tells the model the answer is 3. |

---

## 5. What this row does not cover, and should

### 5.1 The `livecodebench` suite oracle (2,349 live rows) — the actual finding

Retiring the 11 closes the row as written and leaves the larger defect untouched. Recommended, in
order:

1. **Stop scoring `livecodebench` until its oracle is rebuilt.** As with debugbench, live-and-vacuous
   is worse than absent: it contributes confident, meaningless passes to aggregate scores and to
   anything derived from them (item difficulty, `p_correct`, core selection, effort-ladder fits —
   `scripts/analysis/effort_ladder_spec.py:117` advertises livecodebench as a *hard* code suite).
2. **Any past comparison resting on a `livecodebench` delta carries no signal** and should be
   re-derived if it was load-bearing — same disposition as debugbench.
3. **Rebuild via differential execution** against the upstream `python` reference solution, which we
   do have for all 2,360 problems. That is the only oracle the source can support.
4. **Fix `LiveCodeBenchAdapter` before any pool rebuild.** Two changes, not one: the
   `# assert` comment prefix *and* `_extract_test_cases`. Fixing only the prefix converts 11 silent
   drops into 11 systematic failures.

### 5.2 The generalising guard (implemented with this audit)

`vacuous_rows` asks *"is the oracle satisfied by echoing the input?"*. It needs a sibling:
**"is the oracle the same on every question in the suite?"** A substring-family `expected` that is
constant across a whole suite grades *format*, not *answer* — it cannot distinguish question 1 from
question 2,360, so it cannot be measuring either.

Measured over all 39 suites in the pool (n ≥ 20, `expected` constant):

| suite | n | `expected` | scoring | verdict |
|---|---|---|---|---|
| `livecodebench` | 2360 | `"def "` | **substring** | **VACUOUS — the oracle IS `expected`** |
| `needle_parameterized` | 25 | `"eat a sandwich and sit in Dolores Park on a sunny day"` | **substring** | by design (one needle, varied depth/length) — flagged, and correctly so: one fixed needle is memorisable |
| `bigcodebench` | 1140 | `"task_func"` | code_execution | fine — 1,139 distinct `test_code`, oracle is elsewhere |
| `usaco` | 520 | `""` | code_execution | fine — 511 distinct `test_code` |
| `instruction_precision` | 541 | `""` | programmatic/substring | fine — needle in `scoring_config` |

Restricting the check to substring-family scoring separates the one real defect from the three
false positives and leaves one honest by-design flag. **Shipped**: `constant_oracle_suites()` in
`epyc-orchestrator/scripts/autopilot/core_v2_select.py`, wired into `write_core_jsonl` next to
`vacuous_rows`, with 7 unit tests in `tests/unit/test_core_pool_vacuous_oracle.py` — orchestrator
commit `ea71c3be`. Run against the live pool it returns exactly the two rows of the table above.

It is computed over the **source** pool, not the emitted core rows — on a 50-row core a suite
contributes 1-3 rows and constancy is coincidence, so computing it there would be a guard that
passes for having too small an input to disagree. Two mutations were applied and both were caught
by the tests: deleting the substring restriction (`bigcodebench` false-positives) and deleting the
minimum-rows threshold (3-row suites flagged).

---

## 6. Scope and limits, stated

- The 13 is **complete, not sampled** — the predicate was run over all 79,479 rows of the live pool.
- The pool is **gitignored**, so none of it is verifiable against git. Everything in §0-§3 is
  verifiable against the file on disk (mtime 2026-08-04 07:02:15Z, 1,350,221,880 bytes) and against
  the two upstream HF snapshots, which are content-addressed and are.
- **I could not establish where the "14" came from.** The metadata-line hypothesis is plausible and
  unproven; the original counting script was not persisted.
- I did **not** verify that `debug_scorer` behaves as `eval_tower`'s predicate implies for every
  scoring method — I transcribed the tower's *gate*, which is what decides whether a row is dropped.
  A row this audit calls scoreable could still be mis-scored downstream; that is a different check.
- I did **not** modify the question pool, the core pools, the `mode_advantage_hard.yaml` source, the
  LeetCode adapter, or any handoff. §4's decisions are decisions, not applied changes; §5.1's
  remediation needs the eval-pipeline owner and a pool rebuild. The only code shipped with this
  audit is the §5.2 guard and its test.
- Read-only over all data throughout; no inference window used or requested.
