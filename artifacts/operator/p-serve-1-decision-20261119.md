# P-SERVE-1 — operator ratification package (AutoKernel box RATIFY-MEAS-2)

Prepared 2026-11-19 by an agent. **Not applied.** Only the operator applies it: `MEASUREMENT.md` and
`measurement/protocols/*.md` are human-amendment-only (`coordination/session-bus/human_only_paths.yaml`).

## The gap

`MEASUREMENT.md` §2 has no protocol row for the kernel-champion **serving A/B instrument**: the harness
that produces the serving floor, the serving gate and the production headline (`instrument_class=serving`,
INSTRUMENT-CLASS-1). Every serving number the AutoKernel campaign quoted therefore cites no protocol,
including the floor and the gate that held the champion at `445e93a8`, and is admissible only as an
observation. It was deliberately left out of RATIFY-MEAS-1 (ratified 2026-09-08) because a new protocol
needs annex text. It is distinct from P-SERVE-SEL-1 (Annex Q: selection-policy load sweeps, orchestrator
in the loop, unit = arm).

## What you are ratifying

`P-SERVE-1`, appended to **Annex K** (`measurement/protocols/kernel-research.md`, +239 lines), plus one
§2 registry row and one CHANGELOG entry in `MEASUREMENT.md` (+10 lines). Additions only. The annex text
(`artifacts/operator/staged/p-serve-1-20261119.md`) **describes what the code already enforces**, citing
`file:function` in `epyc-inference-research` main `a794f5b54`
(`scripts/kernel_rnd/autokernel/loop/`). No threshold, gate or code changes.

| Section | What it fixes | Enforced by |
|---|---|---|
| Recipe | `recipe_hash`; launch argv; resolved-recipe build digests (executable, DSOs, model, drafter); paired ABBA (`matched_process_v2`, 1-64 pairs, seeded counterbalanced order); `np` slots; frozen `request_digest`; env readback; cpu_list pin | `serving.py`: `Recipe.recipe_hash`, `server_argv`, `_matched_plan`, `_frozen_requests`, `verify_env_readback`; `resolved_recipe.py`; `serving_gate.py`: `classify_e2e_design` |
| Residency (R23-60) | sampled across the whole launch; `proven` needs the window to contain the request phase and >= 1 GiB VRAM plus the three HIP legs; `refuted` raises `ServingNotResident`; unsampled is `unproven` | `serving.py`: `_residency_record`, `_refuse_if_not_resident`, `_residency_fold`; `hip_launch_proof.py` |
| Unit | `process`, derived from the harness (FLOOR-UNIT-1) | `serving.py`: `COMPARE_EFFECT_UNIT`; `floor_units.py` |
| Floor | `unit`, `n`, interval, `recipe_hash`, `request_digest` required; matched floor n in 24-256; degraded-host guard re-measures, never silently drops | `serving.py`: `write_floor`, `calibrate_floor`, `_validate_matched_floor`, `_apply_outlier_guard` |
| Headline | >= 14 independent launches per arm (28 total) at sd 2.793%, MDE 3.0%, alpha .05, power .80; below it `HeadlineInadmissible` | `headline_admissibility.py`; `production.py` |
| Gate | unit mismatch / absent / unit-less / n-less / other-recipe floor refuses before any spend; `decisive = abs(effect) >= floor`; `PROMOTE` only for decisive, positive, non-regressing | `serving_gate.py`: `main`; `serving.py`: `compare`, `check_unit`; `accumulate.py`: `classify_serving` |

## Gaps the code has against its own rules (listed in the annex, NOT changed here)

The annex has an *Enforcement state at ratification* block so a green gate is not read as full coverage.
Each item is a code change for the owning AutoKernel session and is independent of your signature:

1. FLOOR-UNIT-1 Rule 2 (`n >= 24`) is enforced for the matched floor only; a legacy `serving_floor.v1`
   with `n < 24` still gates (`recal_serving_floor.py` defaults to 5 samples; `FloorReading.gate_floor`
   checks only that `n` is stated).
2. Residency is provenance, not a gate input: an `unproven` row can still be `decisive`.
3. A floor with no `recipe_hash` (`unverified`) is used, announced and stamped; only a disagreeing hash refuses.
4. The `legacy_v1` row carries no binary digest.
5. Headline admissibility is enforced in `production.py`, not in `serving_gate.py`.

## Judgement points for you (strike any in review; the bundle is regenerated, never fuzzed)

- **Annex K, not Q or a new annex.** Reason in `staged/p-serve-1-20261119.measurement-md.md`.
- **Date.** The registry row and annex heading read 2026-11-19, the date of the staged text. If you sign
  later, the receipt's `applied_at` is the signing time. Say so and I regenerate with the later date.
- **Grammar clause.** A GPU serving claim quotes `residency=<status>`; a serving number that cites no floor
  unit is an observation. This names a field the code already writes; it adds no refusal.

## The one command

```
bash /mnt/raid0/llm/epyc-root/scripts/operator/run_p_serve_1_ratify_20261119.sh --operator <your-name>
```

It fetches, creates an isolated worktree off `origin/main`, shows the preflight and the full diff, asks you
to type `RATIFY`, applies, verifies and stops without pushing. The signer is typed: an unset name, a
system account (`node`, `root`, `id -un`) or an agent id is refused. Read-only review without the wrapper:
`bash scripts/operator/ratify_p_serve_1_20261119.sh --review`.

## Pins (any mismatch refuses; stale or moved target means regenerate, never force)

| item | sha256 |
|---|---|
| patch `artifacts/operator/p-serve-1-20261119.patch` | `a63ca5e4e30a03cba1f209ceee94ec1895301916dbb4de7c79f86c4fc17dd73b` |
| staged annex `staged/p-serve-1-20261119.md` | `e48cfbb5c6420d153cb1c81a6235475fa5b4ac095a0c7662dec3729f22a4d364` |
| staged snippets `staged/p-serve-1-20261119.measurement-md.md` | `9210c1a7765970b0dea1df02f1d466b80117b07a6c5dfe48066a3209047b7ad9` |
| `MEASUREMENT.md` pre / post | `bd9f2762...b8` / `92199cbb...52` |
| `kernel-research.md` pre / post | `c086e4ee...15` / `c5bd00d7...4e` |

## Apply test (agent, in a throwaway worktree, `ROOT=` that path, never `/workspace`)

Dry review passed preflight; `--apply` without a signer refused (exit 65); `--apply` with a typed signer
applied, the section-5 consolidated receipt returned RATIFIED, a private-index commit of exactly five paths
went through the real commit hooks, `--verify` passed, and a re-run printed ALREADY RATIFIED without
writing. A tampered staged annex and a moved `MEASUREMENT.md` were each refused. The throwaway worktree was
removed.

## Not granted

No measurement, compute window, threshold or code change; no earlier serving number is re-verdicted. After
you sign, the owning session closes the RATIFY-MEAS-2 box with a belief tag.
