# Ratification note — REG-ENF-1 / REG-ENF-2 (branch `rtg34-regenf-20261110`, not pushed)

**Asks for:** the operator's signature on one trust-boundary change: a new PreToolUse hook wired
into `.claude/settings.json`. Everything else on the branch (the registry, its validator and
the tests) is ordinary code. It is listed here because the registry describes the hook surface.

## What changes

1. **REG-ENF-2: a new hook, `scripts/hooks/check_inference_region_claim.sh`**, with its scanner
   `inference_claim_scan.py`. It is wired as PreToolUse/Bash right after `check_destructive_git.sh`.
   It refuses (exit 2) an agent-typed inference launch when no region claim wraps the launch.
   Launch binaries: `llama-server`, `llama-bench`, `llama-cli`, `llama-perplexity`,
   `llama-batched-bench`, `llama-speculative*`, `llama-mtmd-cli`, `whisper-cli/server/bench`, and
   others listed in the scanner. Two forms count as a claim:
   - a `flock` on `cpu_region.*.lock`, `gpu_device.*.lock` or `gpu_quiet.lock` that wraps the
     launch, either in the same segment or in its `-c` body;
   - the calendar engine `filler_run*.sh`.

   Seeing that a lock is held does not count, because of invariant 5. `--help`, `--version` and
   `--list-devices` pass. The scanner looks only at invocations: a mention in a heredoc, a quote,
   a comment, a grep, an echo or a commit message passes.
2. **REG-ENF-1: `docs/reference/governance/rule_registry.json`.** It has 38 rules: 19 hard, 8 soft
   and 11 prose. Each row carries `enforcement_class` and `enforcement_points`.
   - `scripts/governance/rule_registry.py --check` verifies these things:
     - each source anchor exists word for word;
     - each hook point is wired in settings.json under its event and matcher;
     - **every hook wired in settings.json has a registry row**, so no enforcement goes
       unregistered;
     - the git-hook points are installed;
     - the opencode deny block exists;
     - the generated `RULE_REGISTRY.md` is fresh.
   - `--render` regenerates the prose surface.
   - settings.json is not generated. It is a trust boundary, so its parity is checked instead.

## Posture

| Condition | Result |
|---|---|
| A launch is detected and no claim wraps it | **fail closed** (exit 2) |
| The scanner is missing or errors | fail closed only for the unambiguous form (a launch binary at a command position and no region-lock path anywhere in the text); otherwise pass |
| jq is missing or the hook input cannot be parsed | **fail open** |
| `EPYC_ALLOW_UNCLAIMED_INFERENCE=1` in the session environment | allow (operator override; it cannot be set from the command text) |

## Blast radius

- Affected: every Claude Code session on epyc-root that types a raw inference launch into Bash.
  This includes the workflows in docs that show a bare `llama-bench` or `llama-server` line.
  Those sessions now have to wrap the launch in `flock <region lock>` or use the calendar engine.
- Not affected:
  - launches made inside scripts, such as `orchestrator_stack.py`, filler engines and benchmark
    drivers, because the hook sees only the command text;
  - Codex and opencode sessions, which do not have this hook;
  - git hooks.
- Known limits:
  - The hook checks that a claim is acquired. It does not check that the claimed region covers
    the `taskset` footprint. `grant_ok_launcher.py` and `cpu_region_claim.check_footprint_covered`
    still own that check.
  - A launch through a variable (`$BIN -m x`) is not detected.

## Rollback

Delete the `check_inference_region_claim.sh` entry from `.claude/settings.json`, or revert the
REG-ENF-2 commit. If only the settings entry is removed, the registry's `--check` then reports the
`INF-REGION-CLAIM` row as "not wired". To stand the hook down cleanly, either revert both commits
or change that row to `soft` with a validator point. For an immediate per-session bypass without
a commit, set `EPYC_ALLOW_UNCLAIMED_INFERENCE=1`.

## Tests

- `scripts/hooks/tests/test_inference_region_claim.py`: 20 fixture cases (8 block, 12 allow) plus
  posture tests (override, other tools, unparsable input, missing scanner). All pass.
- `scripts/governance/tests/test_rule_registry.py`: the live registry is clean, plus 10 mutation
  tests. All pass.
