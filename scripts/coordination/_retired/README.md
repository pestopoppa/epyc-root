# `scripts/coordination/_retired/` — quarantined delivery-plane machinery

Code in here is **not dead and not deleted — it is out of the loop**. Nothing on the
live path imports it, no daemon calls it, and it is not registered in any CLI a
scheduler reaches. It stays runnable by hand and stays tested.

Why a quarantine directory rather than a deletion or a comment block:

- **Deletion loses a measured remedy.** Every module here was written in response to a
  specific, expensive incident, and its guards are calibrated against measurements
  nobody wants to repeat under pressure. Re-deriving one at 3 a.m. is how the fleet
  got four uncoordinated calibrations of "is this session alive" in the first place.
- **Commenting it out in place is worse than both.** Dead code inside a live module
  still gets read as if it ran, still shows up in every grep, and still has to be
  reasoned about by the next person editing the file around it.

The rule for anything in here: **if you find yourself wanting it back on the live path,
that is a design change with a handoff row, not a one-line import.**

| Module | Retired | Why | Origin incidents |
|---|---|---|---|
| `composer_repair.py` | 2026-08-16, P3-2 | The machine no longer sweeps or repairs pane composers. Only two interactive endpoints remain (`inference`, `coordinator-agent`) and the operator sits in front of both; pool-worker panes are human-only under D8, and their completion signal is a report file, never pane state. Zero live callers at retirement (verified across `scripts/`, `.claude/`, hooks, tests, docs). | C51 (detector), C54 (clear/submit), C55 (wake character), H-1, H-2 |

## Running one by hand

```bash
python3 scripts/coordination/_retired/composer_repair.py pending
python3 scripts/coordination/_retired/composer_repair.py clear  --agent <id> --expect '<text>'
python3 scripts/coordination/_retired/composer_repair.py submit --agent <id> --expect '<text>'
```

These import their shared read substrate from `../tmux_adapter.py` by name — they own
no second copy of the glyph table or of the C51 submission-verification chain, because
a duplicated calibration is a calibration that drifts.

## Tests

`scripts/coordination/tests/test_tmux_adapter_submission.py` still owns the C51/C54/C55
cases; its `_load_repair()` helper loads this directory's module against a
temp-rooted adapter instance. `tests/test_tmux_adapter.py::test_h2_both_key_paths_go_through_one_helper`
parses BOTH files, because H-2's two key paths now live apart and that makes drift
easier, not harder.
