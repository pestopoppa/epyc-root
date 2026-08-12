# Operator signature package — 2026-08-12 coordinator-seat refactor

**Two amendments requiring the operator's own hand.** Both were authorized in principle during the
2026-08-12 plan review; neither can be applied by an agent, because both live behind the trust
boundary and the boundary is human-amendment-only by construction.

This file is a *proposal*. Nothing here has been applied.

---

## 1. AUD-15 — gate the auto-loaded instruction surfaces

### The gap, verified

`CLAUDE.md`, `agents/AGENT_INSTRUCTIONS.md` and `agents/shared/*.md` load into **every** session at
startup. `CLAUDE.md` already requires explicit operator approval for sub-agent edits to instruction
surfaces — and **nothing enforces it**. Measured on 2026-08-12:

- `.claude/settings.json` registers eight `Write|Edit` `PreToolUse` hooks; **not one** guards these
  paths as an instruction surface.
- `agents_schema_guard.sh` and `agents_reference_guard.sh` check **shape** only, and the latter's
  path case lists `CLAUDE_GUIDE.md`, not `CLAUDE.md`.
- Commit `2f787163` (2026-08-12 10:28:27Z) edited `CLAUDE.md` (+6) and
  `agents/AGENT_INSTRUCTIONS.md` (+4) with no pre-edit ask, no token, no receipt, no bus
  `decision-request`. The edit's content was right; the absence of a gate is the finding (F-19).

### Why it matters more than an ordinary policy file

A wrong premise on an auto-loaded surface becomes **five sessions' truth at once**. F-21 is the
proof: the false claim *"uncommitted work does not survive a reboot"* was broadcast fleet-wide and
is the stated reason one main committed another agent's work. Broadcast is the amplifier that makes
this class P1 rather than P3.

### Proposed amendment

Add three entries to the `paths:` block of `coordination/session-bus/human_only_paths.yaml`,
immediately after the `agents/shared/MEASUREMENT_POLICY.md` entry:

```yaml
  - repo: epyc-root
    glob: "CLAUDE.md"
    why: "auto-loaded instruction surface; a wrong premise here becomes every session's truth"
  - repo: epyc-root
    glob: "agents/AGENT_INSTRUCTIONS.md"
    why: "auto-loaded instruction surface; same amplifier as CLAUDE.md"
  - repo: epyc-root
    glob: "agents/shared/*.md"
    why: "shared policy loaded by every role overlay; MEASUREMENT_POLICY.md is already listed and this generalises it"
```

### Cost, stated honestly

Every policy edit then needs an operator signature — including routine ones. `2f787163` would have
been gated; so would this refactor's own Phase-1 edits to `agents/coordinator-agent.md` (that file
is a *role overlay*, not `agents/shared/`, so it stays ungated under the proposal as written — if
you want role files gated too, add `agents/*.md` and accept the extra friction).

Layer 2 of `check_trust_boundary_edit.sh` is **best-effort by design**: if the gate list cannot be
parsed it ALLOWS and warns, because failing closed on an unreadable config would block every edit in
the repo. So this gate is a strong speed bump, not a containment boundary — unlike Layer 1, which is
unconditional. Say so plainly rather than over-claiming it.

### To apply (operator, two steps — both human actions by contract)

```bash
# 1. edit the gate list by hand (the Write/Edit hook blocks agents, not you)
$EDITOR coordination/session-bus/human_only_paths.yaml

# 2. rewrite the pin so `session_bus.py validate` and the daemon audit agree
sha256sum coordination/session-bus/human_only_paths.yaml | awk '{print $1}' \
  > coordination/session-bus/human_only_paths.sha256

# 3. verify
python3 scripts/coordination/session_bus.py validate
```

**Default if unanswered: the gap stays open.** F-19 recurs the next time a subagent is pointed at an
instruction surface, and nothing in the repo will stop it.

---

## 2. P-GPU-1 field 3 — name the verifier-produced linkage receipt

### The gap, verified

`measurement/protocols/gpu-cross-device.md` field 3 already requires `LD_LIBRARY_PATH` and the
backend list among the mandatory evidence fields. What it does not say is *how that evidence is
produced* — and a **hand-recorded env string cannot distinguish a HIP run from a CPU-fallback run**:

- llama.cpp **dlopens** `libggml-hip.so`, so the executable shows zero HIP linkage either way and
  `ldd` on the binary cannot settle it (INC-20260731).
- `/etc/environment` was cleaned 2026-07-31, but every long-lived container still carries the
  pre-fix `LD_LIBRARY_PATH` that puts the CPU-only build first. On 2026-08-12 this reproduced from
  two independent directions on the same day.
- `verify_ggml_linkage.sh /bin/true <tree>` printed **PASS** and exited 0: exit status alone could
  not distinguish *all libs correct* from *no libs inspected*. (The intrinsic non-vacuity fix is
  ordinary work and is being landed separately in this refactor's Phase 5.)

### Proposed amendment — one clause added to field 3

> 3. **Binary/model identity** — exact worktree, branch, commit, binary path, `LD_LIBRARY_PATH`,
>    backend list; exact model path, mmproj (if used), quant, context, KV quant,
>    reasoning/sampling flags, spec-dec mode. **The `LD_LIBRARY_PATH`/backend evidence is satisfied
>    ONLY by a verifier-produced linkage receipt captured against the running binary — verifier id
>    and version, the inspected library set with per-library resolved path and sha256, and the
>    verdict — never by a recorded environment string alone. A receipt that inspected no libraries
>    is vacuous and does not satisfy this field.**

### Why now, and why it costs nothing extra

The receipt schema **already exists twice** in the codebase — AutoKernel's `LinkageEvidence`
(`t0_provider.py`) and the laguna runners' `binary_identity.json`. The Phase-5 launcher gates
produce exactly this artifact automatically, so from then on decision-grade GPU runs carry the
receipt whether or not the constitution names it. Amending merely closes the case where someone
hand-records the fields and the number is formally claim-eligible while the binary ran on CPU.

### Interaction with the retro-certification already run

`:50-54` (retro-certification) is unchanged by this amendment. The Phase-7 audit note
(`docs/reviews/gpu-linkage-retro-certification-20260812.md`) classifies the in-window artifacts
under the **current** text; the amendment governs future claims only, and should not be applied
retroactively to re-grade artifacts already dispositioned.

### To apply (operator)

`measurement/protocols/*.md` is on the human-only gate list. Amend by hand, then:

```bash
python3 scripts/coordination/session_bus.py validate     # gate-list pin unaffected; sanity check
```

Per `MEASUREMENT.md` §amendments: append or version, never silently rewrite — record the amendment
with its date and rationale in the protocol's own amendment log.

**Default if unanswered: the mechanisms still ship** (launcher gates, receipts, the intrinsic
non-vacuity fix), and the constitutional text keeps permitting a hand-recorded env string.

---

## Provenance

Both items were surfaced by the 2026-08-12 coordinator-role audit sweep and recorded as AUD-15 and
the P-GPU-1 strengthening in
[`handoffs/active/coordinator-role-failure-modes-and-refactor.md`](../../handoffs/active/coordinator-role-failure-modes-and-refactor.md).
Neither was applied by an agent; this package exists so the operator can apply both from one place
with the evidence attached.
