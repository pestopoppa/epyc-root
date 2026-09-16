---
name: security-review
description: Use when reviewing a diff, commit, PR, dependency change, agent/tool change, or codebase surface for security risk. Runs a STRIDE + OWASP Top 10 + OWASP LLM + supply-chain review: candidate discovery, pre-validation dedup, production-reachability GATE-0, exploit-path gates, and mandatory refutation, with P0-P3 severity.
---

# Security Review

Use this skill for focused security review. It complements general code review: emit only security findings with a plausible exploit path, or say no exploitable issue was found. The dedicated slash command wrapper lives in `.claude/commands/security-review.md`.

## Inputs

- Review scope: uncommitted diff, branch/base diff, commit, PR, file list, or subsystem.
- Trust model: auth/authz assumptions, exposed endpoints, deployment mode, secrets handling, and whether local-only access is acceptable.
- Optional focusing docs: `threat-model.md`, architecture notes, API docs, dependency policy, prior incidents.

If no scope is given, inspect the current diff first.

## Workflow

1. **Scope and evidence**
   - Identify entrypoints, changed files, new dependencies, config/infra changes, agent/tool permissions, and generated artifacts.
   - Read only the code needed to trace changed data flows. Use GitNexus impact/context before code edits or refactors; use `rg` for exact strings.
   - If a `threat-model.md` exists in scope, read it before assigning severity.

2. **Pass 1: Candidate discovery**
   - Trace changed data flows across trust boundaries: auth, authz, validation, database, network, filesystem, subprocess/shell, secrets, dependency install/build, and LLM/tool execution.
   - Apply STRIDE: spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege.
   - Apply OWASP Web/API Top 10 themes: access control, crypto/secrets, injection, insecure design, security misconfiguration, vulnerable components, auth failures, integrity failures, logging/monitoring gaps, SSRF.
   - Apply OWASP LLM Top 10 2025 themes when agents, prompts, tools, RAG, MCP, evals, or model outputs are involved: prompt injection, sensitive information disclosure, supply-chain risk, data/model poisoning, improper output handling, excessive agency, system prompt leakage, vector/embedding weaknesses, misinformation/overreliance, unbounded consumption.
   - Apply supply-chain checks for new or changed deps: lockfile drift, broad ranges, typosquatting, install scripts, vendored binaries, generated code, abandoned packages, license/security-sensitive transitive deps.
   - Record every candidate with the fields the next stages need:
     - `path`: repo-relative.
     - `start`–`end`: a line RANGE. A single line has `end = start`.
     - `cwes[]`: a SET of CWE ids. Any member may match.
     - `category`: the STRIDE/OWASP class.
     - The sink.
     - One sentence of hypothesis.

3. **Dedup: before any validation**
   Collapse duplicate candidates *before* Pass 2, so no candidate is validated twice. The placement comes from CodeCrucible and the key from benchmrk's matcher (`security-review-skill.md`, intake-943/948).

   Two candidates are the same finding only if all three hold:
   - **Same file.** Normalise paths first: strip container mounts (`/target/`, `/src/`, `/app/`) and make them repo-relative. A path you can only match by an ambiguous suffix is **not** a match.
   - **Overlapping line ranges.** The ranges must overlap; start-line equality is not enough. A line-exact key fails in both directions: two unrelated classes on one line collapse into one, and one finding whose line moved under a reformat survives twice.
   - **Related classes.** Some CWE in one set is identical to, or the direct parent or child of, some CWE in the other. A shared *pillar* (CWE-284, -435, -664, -682, -691, -693, -697, -703, -707, -710) does not count: everything meets there. Without CWEs, the `category` must be equal.

   When two candidates merge:
   - Keep the union of their evidence, ranges and CWE sets, under the most specific title.
   - Never drop one silently. List each merge under **Checks run**.
   - Keep the result deterministic: process candidates in a stable order (path, start, end, first CWE). Merge each one into the earliest existing candidate it matches.
   - Same line but unrelated classes means two candidates, not one.

4. **Pass 2: Validation — reachability FIRST, then exploitability**

   **GATE-0 — production reachability.** Decide this before any exploit reasoning. It is cheap, and it keeps the expensive analysis off dead code.
   - Is the code path reachable in the deployed configuration? Trace it from a real entrypoint: an API route, CLI, scheduled job, tool/MCP registration, or agent tool list.
   - Check reachability against:
     - feature-flag and config **defaults**
     - the launch manifest and service registry
     - import-time wiring
   - Test-only code, dev scripts, default-off flags, unregistered tools and unreferenced modules are **not reachable**. Say which of these applies and cite the evidence (the flag default, the missing registration, the zero callers from `gitnexus impact`/`rg`).
   - An unreachable candidate stops here. Record it under **Residual risk** as `unreachable in production: <evidence>`, including what would make it reachable. Do not reason about its exploitability, and do not give it a severity.

   **GATES 1–8 — exploit validation**, only for candidates that passed GATE-0. Promote a candidate only if all of these hold:
   1. Attacker capability is realistic for this deployment.
   2. Attacker-controlled input reaches the code path.
   3. A trust boundary is crossed or a security invariant is weakened.
   4. A vulnerable sink or privileged action is reachable.
   5. Existing validation, sandboxing, feature flags, authz, or deployment constraints do not already block it.
   6. Impact is concrete: data exposure, unauthorized action, code execution, durable prompt/tool compromise, integrity loss, availability loss, or secret leakage.
   7. A minimal fix is clear.
   8. File/line evidence is available.

   If any gate fails, do not promote the candidate. Mention it under residual risk only if it is worth tracking.

5. **Mandatory refutation: no CONFIRMED without an attempt to refute**
   A candidate that passed every gate is still only `PROPOSED`. Before it becomes `CONFIRMED`, try to break it yourself. This is on top of the gates, not a replacement for them.
   - Write the **strongest** counter-argument you can find. For example:
     - a sanitiser or authz check in a caller or middleware
     - a type or schema constraint that rejects the payload
     - a sandbox or deployment boundary (local-only bind, container, `--network none`)
     - a config default
     - an attacker capability the threat model rules out
     - an earlier return that makes the sink unreachable with attacker input
   - Check that counter-argument **against the code**, with file/line evidence. Do not check it against intuition.
   - **Refuted:** drop the finding to residual risk as `refuted: <evidence>`.
   - **Survives:** mark it CONFIRMED and record the refutation that was attempted and why it failed.
   - A finding with no recorded refutation attempt is not emitted. "I could not think of one" is not an attempt: name at least one mitigation class you checked and where you checked it.

6. **Severity**
   - `P0 / Critical`: unauthenticated or low-friction RCE, credential/key exfiltration, broad tenant/user data exfiltration, auth bypass for privileged actions, durable agent/tool compromise with high agency.
   - `P1 / High`: authenticated privilege escalation, scoped secret disclosure, SSRF to sensitive internal systems, injection into privileged tools, supply-chain change likely to execute attacker code.
   - `P2 / Medium`: meaningful security invariant weakening with narrower reach, DoS with realistic cost, unsafe LLM/tool behavior requiring specific conditions, missing validation on sensitive but non-critical paths.
   - `P3 / Low`: defense-in-depth gap with a credible but limited path, logging/audit weakness, hardening issue that does not currently expose sensitive impact.

   Do not assign P0-P2 without a concrete exploit path. Do not inflate severity for theoretical misuse.

## Output

Lead with CONFIRMED findings ordered by severity. Use this schema:

```markdown
- [P1] Imperative title under 80 chars
  - Location: path/to/file.ext:123-130
  - Class: CWE-78 (CWE-77) · OWASP A03 Injection
  - Problem: What security invariant is broken.
  - Reachability (GATE-0): entrypoint -> ... -> this path, with the flag/config default that enables it.
  - Exploit path: Attacker input -> trust boundary -> vulnerable sink -> impact.
  - Refutation attempted: strongest counter-argument checked (where) and why it does not hold.
  - Suggested fix: Minimal safe change.
```

After findings, include:

- **Residual risk**: every candidate that did not reach CONFIRMED, each with its reason. The reason is one of:
  - `unreachable in production: …`, from GATE-0.
  - `gate N failed: …`, from gates 1–8.
  - `refuted: …`, from the refutation stage.
  - Open uncertainty.
- **Checks run**: the commands and code paths inspected, plus the dedup merges: which candidates were collapsed, and on which key.

When a finding is recorded as a labelled gold annotation (a corpus row, not a review comment), use the ONE dual-gold schema. That is `epyc-orchestrator` `orchestration/gold_annotation.schema.json` with `src/proactive_delegation/gold_annotations.py`, owned by `reviewer-typed-artifacts.md` RA-9 (on branch `sub/reviewer-artifacts-20260916` until it merges). Map `Class` to its `cwes[]`/`category`, and record a refuted or unreachable candidate that is worth keeping as a `status: invalid` decoy. Never define a second schema here. Machine-generated annotations must pass the same module's gold-sanity gate (`gold_sanity.run_gate`) before they are admitted.

If no findings pass the gates, say so explicitly and name the highest-risk surfaces inspected.

## Guardrails

- Do not output generic checklist results as findings.
- Do not recommend broad rewrites when a narrow guard, validation, permission check, dependency pin, sandbox, or output encoding fix closes the path.
- Do not expose secrets discovered during review; identify the file/path and remediation class only.
- Do not run exploit payloads against live services unless the operator explicitly asks and the target is isolated.
- Do not rewrite historical records to remove leaked data; append remediation notes and rotate/revoke secrets instead.
