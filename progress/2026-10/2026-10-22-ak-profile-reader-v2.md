# 2026-10-22: AutoKernel CPU profile reader v2 (sampled-CPU topology), coordinator 3c4ca599

Follows `2026-10-22-vidya-test-fixes.md`. That shard recorded 15 real failures with
`EPYC_RESEARCH_ROOT` set: 12 in `test_autokernel_profile_adapter.py` and 3 in
`test_loop_cpu_profile_adapter.py`. They had one root cause. Research `07333b884` (2026-09-17)
changed the producer's capture shape, and the ROOT reader still pinned the old shape. Owner tasks:
AKU-06q and VB-AK-UNIFIED-PROFILE. No inference was run.

## What changed (`scripts/vidya/adapters/autokernel_profile.py`)

- **Versioned reader.** There are two closed `CaptureVersion`s, `LEGACY_CAPTURE` (`legacy-v1`) and
  `SAMPLED_CPU_CAPTURE` (`sampled-cpu-topology-v2`). `capture_version()` reads the version from the
  receipt's own `perf record` commands, using the producer's discriminator: `--sample-cpu` in the
  record tool command. The flag must be present in every readable phase or in none; a mix is
  refused. A phase whose command cannot be read decides nothing, and the structural checks refuse it.
- **Legacy reader is unchanged.** It uses the same fields, limitations and source allow-lists as
  before, and its refusal messages are byte-identical. Its projection gains no keys.
- **v2 checks.** Each of these must hold:
  - the new limitation text (the producer inserts one line before the last);
  - `kept_scope`, the tuple `extra.limitations`, the source constants and the capture limitations
    all match that version;
  - a per-phase `topology` with schema `epyc.autokernel.cpu_topology.v1`, bounded CPU, NUMA and
    sibling maps, and a `topology_digest` that rederives;
  - `samples.location_periods`. Each row's TID must be in the phase TIDs, and its CPU and NUMA node
    must agree with the topology. Rows must be sorted and unique, and they must rederive the sampled
    total and every TID period;
  - the perf-script `-F` field list includes `cpu`;
  - the source-closure digest is in the v2 allow-list.
- **Pinned digests.** Both come from the producer's own method,
  `lifecycle_observation._digest(cpu_profile.source_identity())`, run on a `git archive` of the commit.
  The closure includes the interpreter, so both were computed under `/usr/bin/python3.13`
  (sha256 `efb29ce5…`):
  - research `07333b884` → `54b4a0ef0df78ddda4ed22802ad84bd498381c00d329fe999c99b7e3678f9686`
  - research main `b93017dc9` → `69dea977d0b0c62e30e5cb7f128e2b26090fcda510b436ec3c357d107146ca19`

  No others are pinned. As a method check, research `83334d892` reproduces the legacy
  `MATCHED_CPU_SOURCE_DIGEST` (`09e80489…`).
- **Projection.** A v2 capture adds only `capture_version` and `sampled_cpu_topology_digests` to the
  rows and to the ClaimTuple `extra`. `_base_claim` and the loop-row equality refuse a row that adds
  or rewrites either key. There is no new grading rule: `claim_tuple.grade()` decides.

## Finding: the legacy allow-list stopped matching before 07333b884

Research `07333b884^` (`91e63313d`) produces closure digest `42f17b7c…`. That digest is not pinned.
Research commits between 09-11 and 09-17 changed files inside the closure:

| Commit | Closure digest |
|---|---|
| `ce751b5df` | `c9142422…` |
| `8b2812098` | `bd9ae2c6…` |
| `7788e8728` | `44b8af00…` |

Captures from those intermediate producers are refused, and stay refused: the brief allowed pins for
07333b884 and current main only. The legacy fixtures therefore come from `83334d892`, the last
legacy closure that is pinned.

## Tests

- New helper `tests/vidya/ak_cpu_profile_producers.py`. It runs the research producers' own
  fixture mode (synthetic perf and a tiny server, no inference), each in its own subprocess. The
  four producers are:
  - `legacy@83334d892`
  - `sampled-cpu@07333b884`
  - `sampled-cpu@b93017dc9`
  - `sampled-cpu@live`, which reads `EPYC_RESEARCH_ROOT` directly and is the conformance tripwire.

  The pinned commits are extracted read-only with `git archive` into pytest temp dirs.
- Every legacy test is kept and now runs against all four producers.
- The 10 substitution refusals and the 2 null-identity refusals now assert their exact message,
  per version.
- New tests:
  - capture version and pinned source digest, per producer;
  - the closed version table;
  - widened `kept_scope`;
  - sampled-field projection, including that the projected keys cannot be forged;
  - 11 v2 refusals: topology absent, topology digest, topology schema, location absent, location
    period, location node, script fields, mixed phases, claims-legacy, legacy limitations, unpinned
    source;
  - 5 legacy refusals: injected topology, injected locations, claims-sampled, sampled limitations,
    unpinned source;
  - 3 loop-path refusals.
- Full `tests/vidya` results:

  | Environment | Passed | Skipped | Failed |
  |---|---|---|---|
  | Default | 2650 | 315 | 0 |
  | `EPYC_RESEARCH_ROOT=/mnt/raid0/llm/epyc-inference-research` | 2896 | 69 | 0 |

  These are from the committed tree (on origin/main `5eb876b71`). The pre-merge base `803da7223` gave
  2634 and 2880 passed, also with 0 failed.

  Of the 69 skips, 23 are version-inapplicable mutation parameters.
- **Caveat.** These pins are strict by design. If research main changes a file inside the closure,
  the `sampled-cpu@live` cases fail until a reviewed digest is added. Running pytest under a
  different interpreter (for example the `.venv` 3.11) also changes every digest.

## Ticks

- `vidya-belief-substrate-program.md`: the VB-AK-UNIFIED-PROFILE sub-item "2026-09-17 sampled-location
  extension" is ticked ✅ 2026-10-22.
- The adapter README row for AutoKernel selected target-profile results records reader v2.
