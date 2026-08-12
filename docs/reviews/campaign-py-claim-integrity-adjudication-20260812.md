# Adjudication — `scripts/kernel_rnd/autokernel/campaign.py`, claim-integrity conflict

**Repo**: `epyc-inference-research` · **Date**: 2026-08-12
**Local** `main` = `4cca1bd7` (untouched; the merge was correctly aborted)
**Origin** `origin/main` = the tip fetched 2026-08-12 · **Merge base** = `0b08ac8e`
Divergence at the time of writing: 14 ahead / 195 behind.

**Routed for adjudication**: the *code* conflict only. The three
`data/batched_decode/**/manifest.json` conflicts are **the operator's to rule on** and are
untouched — see §7.

---

## 1. VERDICT

**They are not alternatives, and they are not even two implementations.**
`origin/main` already contains the local side *verbatim* — same commit, rebased onto a different
base — and adds the claim-open receipt on top of it. All four hunks resolve to **ORIGIN**, and
resolving them to origin loses **nothing**.

On hunk 4, taking the local side would be an **active regression**, not merely a missed improvement
(§5.4).

---

## 2. The decisive fact: `4755e727` and its origin twin are the same commit

| | local | origin |
|---|---|---|
| commit | `4755e727` | `0b44b858` |
| subject | `autokernel: arm the expiry check on the device claim (M3)` | *identical* |
| author / author-date | pestopoppa / `2026-08-12 08:43:12 +0000` | *identical* |
| diffstat | `campaign.py 27 +`, `test_campaign.py 104 +` | *identical* |
| added-line multiset over both files | — | **byte-identical** (`comm` of the sorted `+` lines is empty in both directions) |

The `git patch-id` values differ, which is why the merge does not recognise them as a duplicate:
the two commits were applied to different bases, so their context lines differ. The *content* is the
same commit.

The same holds for the other AutoKernel commit in this lane: local `bff975b2`
(`autokernel: add live GPU device sampling`) has origin twin `3f71a7d0`.

Independent corroboration — for every file involved in the AutoKernel conflicts, every line the
local lane *added* relative to the merge base is already present in origin's blob:

| file | lines added by local | absent from origin's blob |
|---|---|---|
| `campaign.py` | 36 | 2 — both are the *reformatted* `from .execution import (...)` line pair; origin's import list is a strict superset (§5.1) |
| `test_campaign.py` | 104 | 0 |
| `execution/microbench.py` | 58 | 0 |
| `execution/test_device_sampler.py` | 158 | 0 |

All four of the M3 tests added by `4755e727` — `test_the_device_claim_declares_its_hold_window`,
`test_a_raised_hold_window_moves_both_claims_together`,
`TestEveryDeviceClaimSiteDeclaresItsWindow`, `test_the_guard_fails_on_a_call_site_that_omits_it` —
are present on `origin/main`. The AST one-door guard survives the resolution.

---

## 3. What the `max_hold_s` arming guarantees, and what it misses

`acquire_device_claim(..., max_hold_s=float(spec.max_hold_s))` (default `6 * 3600`, one value
declared on `CampaignSpec` and quoted by both the region and device acquirers).

**Guarantees.** Declaring the window is what writes `expires_at` into the claim payload. Without it,
`device_claim.check_claim_expiry()` returns `COULD_NOT_CHECK` forever — *"claim … declared no
maximum hold, so expiry cannot be evaluated"* — instead of a three-valued PASS/FAIL. It is a
**third-party, out-of-process** property: any other session, dashboard, or auditor reading the lock
file can now tell that this claim is overdue and call `request_revocation`. It is advisory and grants
nothing; an expired claim is still never stolen.

**Misses.** It says nothing about whether the claim is *actually held*. A claim can carry a perfectly
valid `expires_at` while its flock excludes no one (see §4). It also only becomes observable *after*
the deadline passes — it is silent for the first six hours, i.e. for the entire duration of a normal
campaign.

---

## 4. What the claim-open receipt / `verify_held` block guarantees, and what it misses

```python
region_receipt = claim.receipt().to_dict()
device_receipts = [held.receipt().to_dict() for held in self._device_claims]
self._claim_open_receipt = {"region": region_receipt, "devices": device_receipts}
self._claim_open_check = schemas.Check.worst_of((
    claim.verify_held(),
    *(device_claim.check_device_claim_held(receipt) for receipt in device_receipts),
))
if self._claim_open_check.outcome != schemas.PASS:
    raise RuntimeError("resource claim could not be verified immediately after acquisition: " ...)
```

**Guarantees.** A **first-party, in-process, at-acquisition** proof that the claim actually excludes
someone right now:

- `cpu_region_claim.…verify_held()` re-reads the machine rather than returning a cached flag. It
  checks that the fd we hold and the path still name the **same inode**, and that the payload read
  back through our own descriptor still carries our `claim_id`. Its docstring names the real failure:
  the region-lock root `/mnt/raid0/llm/tmp` is listed in `storage.EPHEMERAL_ROOTS` as sweepable, so a
  tmp sweep or a disk tidy can leave our flock on an **orphaned inode** while every other actor tests
  a fresh, free file — we stop excluding anyone, nothing errors, and the evidence record still
  asserts the run was claimed. It never returns PASS on an unverifiable claim.
- `device_claim.check_device_claim_held(receipt)` FAILs when the device's payload names a *different*
  claim, and — critically — when the payload names *our* claim but the flock is **free** ("the claim
  leaked and nothing is excluding other processes").

Because the block sits inside the same transactional `try`, a non-PASS raises and the `except
BaseException` path releases every device claim and the region claim. The campaign refuses to start
rather than measuring a contended device.

It is also the **open half of a matched pair**. `close_evaluation_window` repeats the same two checks
at window close, and `_check_same_claim_holder` compares the open and close receipts on
`(claim_id, holder_pid, holder_start_ticks, holder_boot_id)` per plane. All three land in
`WindowAttestations` as `resource_claim_open` / `resource_claim_close` /
`resource_claim_same_holder`. Without `_claim_open_receipt`, the continuity check degrades to
`COULD_NOT_CHECK` — *"claim identity was not retained at window open"* — so dropping the open block
silently disarms a close-side check too.

**Misses.** It is a point observation at t=0. It says nothing about how long the claim may be held
and cannot make a six-hour monopolisation visible to anyone outside this process; `check_claim_expiry`
stays `COULD_NOT_CHECK` without §3.

---

## 5. Hunk-by-hunk

All four hunks: **ORIGIN ⊇ LOCAL**.

### 5.1 Imports (`from .execution import …`)
LOCAL adds `device_sampler`. ORIGIN adds `device_sampler` **and** `control_runner`,
`powercap_broker`, `provider`. Pure textual conflict from re-wrapping the same list. Take ORIGIN.

### 5.2 The claim-acquisition loop
LOCAL: `max_hold_s=float(spec.max_hold_s)`.
ORIGIN: the identical `max_hold_s=float(spec.max_hold_s)` **plus** the receipt/`verify_held` block.
The M3 comment block above the call is *outside* the conflict — both sides carry it identically,
which is itself proof the two commits are the same. Take ORIGIN.

### 5.3 `MicrobenchRunner` spawner kwargs
LOCAL adds the `device_sampler=(RocmSmiSampler(...) if backend == GPU else None)` argument. ORIGIN
adds the identical argument **plus** `host_state=self._read_host_state`. Take ORIGIN.

### 5.4 The uncalibrated-cell banner — *taking LOCAL here is a regression*
BASE had a spurious `f`-prefix on a string with no placeholders. Both sides remove it. ORIGIN
additionally changes `file=stream` → `file=detail_stream`.

That is not cosmetic. ORIGIN introduces `detail_stream = sys.stderr if args.as_json else stream`;
15 human-readable `print(..., file=stream)` sites in the local blob are `file=detail_stream` on
origin, and exactly **one** bare `file=stream` remains. Resolving this hunk to LOCAL would print the
`UNCALIBRATED CELL` banner to **stdout** under `--as-json` and corrupt the JSON payload. Take ORIGIN.

---

## 6. Complementary or alternative — and the recommendation

**Complementary, on different planes**, and *already composed* on origin:

| | plane | observer | window | failure it catches |
|---|---|---|---|---|
| `max_hold_s` | declared deadline in the payload | **third party**, out of process | after the deadline | a claim held past its declared window (the MI210 monopolisation of the night of 2026-08-11/12) |
| receipt + `verify_held` | enforced exclusivity | **first party**, in process | at acquisition, repeated at close | a claim recorded but not excluding — leaked flock, orphaned inode, wrong `claim_id` |

Neither substitutes for the other. A merged version implementing both is strictly better than either,
and `origin/main` **is** that merged version.

> **RECOMMENDATION — resolve all four hunks to `origin/main`, verbatim.**
> The expected post-resolution invariant is stronger than "no conflict markers": the merged
> `campaign.py` should be **byte-identical to `origin/main`'s blob**, and likewise for
> `test_campaign.py`, `execution/microbench.py` and `execution/test_device_sampler.py`. Every line
> the local lane added to those files already exists upstream (§2), so any residual difference is a
> resolution error, not a local contribution. Run the AutoKernel suite afterwards — the four M3 tests
> and the AST one-door guard are the mutation check on this resolution and are present on origin.
>
> Do **not** hand-merge the two blocks into a new third version. The local commits are pre-rebase
> ghosts of commits that already landed upstream; reconstructing them by hand would re-introduce a
> divergence that no longer exists.

**Confidence: high.** The claim rests on an identity (same author, same author-date, same diffstat,
identical added-line multiset), not on a reading of intent.

---

## 7. NOT ADJUDICATED — the operator's to rule on

The full merge has **9 conflicting files** (structurally derived: 65 files modified on both sides,
9 of which conflict under a three-way merge):

| file | hunks | class |
|---|---|---|
| `scripts/kernel_rnd/autokernel/campaign.py` | 4 | code — **adjudicated above** |
| `scripts/kernel_rnd/autokernel/FOOTPRINT.md` | 6 | code/docs — same AutoKernel strand, not adjudicated here |
| `scripts/kernel_rnd/autokernel/execution/microbench.py` | 2 | code — same shape as §5 (origin ⊇ local) |
| `scripts/kernel_rnd/autokernel/execution/test_device_sampler.py` | 1 | code — add/add, origin ⊇ local |
| `scripts/benchmark/run_rocm_saturation_probe.py` | 1 | code — not adjudicated here |
| `artifacts/architect-bench-gpu-20260720/questions_mmlu_pro.json` | 1 | artifact — not adjudicated here |
| `data/batched_decode/e5-gemma-crossbinary-repair-20260812T0745Z/manifest.json` | 1 | **measurement — OPERATOR** |
| `data/batched_decode/e5-gemma-nomtp-v9-20260812T0800Z/manifest.json` | 1 | **measurement — OPERATOR** |
| `data/batched_decode/e5-gemma-nomtp-v9-20260812T0818Z/manifest.json` | 1 | **measurement — OPERATOR** |

**The three `manifest.json` conflicts are behind the human-amendment-only measurement trust boundary
and are explicitly NOT ruled on here.** They are the operator's decision and no agent should resolve
them.

The observed asymmetry, stated as fact and nothing more:

| manifest | local `main` | `origin/main` |
|---|---|---|
| `e5-gemma-crossbinary-repair-20260812T0745Z` | `"void": true` + `void_detail` (declared `2026-08-12T09:10:00Z` by `mainA`) | no `void` key |
| `e5-gemma-nomtp-v9-20260812T0800Z` | `"void": true` + `void_detail` (same declaration) | no `void` key |
| `e5-gemma-nomtp-v9-20260812T0818Z` | `"void": false` + `void_detail` (same declaration) | no `void` key |

The markers come from local `4cca1bd7` (*"E5: machine-readable void markers — assert the status,
never infer it from a missing key"*), which has **no twin on origin** — unlike the sweep commit
`703a80a2` beneath it, which does. Resolving these to origin would silently drop a void declaration
on two runs declared VOID; resolving them to local asserts a status over an origin-side record this
review has not audited. Either direction is an amendment to measurement evidence. **Operator ruling
required.**

---

## 8. Reproducing this review (read-only; the merge was not attempted)

Every finding below was produced without touching `main`, without a merge, and without a worktree in
the shared clone — the three blobs were extracted with `git show` and compared with `git merge-file`
in a scratch directory.

```bash
R=/workspace/repos/epyc-inference-research
B=$(git -C "$R" merge-base main origin/main)          # 0b08ac8e

# the four hunks, in diff3 form, without merging anything
P=scripts/kernel_rnd/autokernel/campaign.py
git -C "$R" show $B:$P > /tmp/base.py
git -C "$R" show main:$P > /tmp/out.py
git -C "$R" show origin/main:$P > /tmp/ori.py
git merge-file --diff3 -L LOCAL -L BASE -L ORIGIN /tmp/out.py /tmp/base.py /tmp/ori.py

# the twin
git -C "$R" log --oneline $B..origin/main --grep="arm the expiry check on the device claim"
git -C "$R" show 4755e727 --format="" -- $P scripts/kernel_rnd/autokernel/test_campaign.py \
  | grep '^+' | grep -v '^+++' | sort > /tmp/a
git -C "$R" show 0b44b858 --format="" -- $P scripts/kernel_rnd/autokernel/test_campaign.py \
  | grep '^+' | grep -v '^+++' | sort > /tmp/b
diff /tmp/a /tmp/b && echo "same commit"
```
