---
name: security-review
description: Use when reviewing a diff, commit, PR, dependency change, agent/tool change, or codebase surface for security risk. Runs a two-pass STRIDE + OWASP Top 10 + OWASP LLM + supply-chain review with exploit-path-gated findings and P0-P3 severity.
---

# Security Review

Use this skill for focused security review. It complements general code review: emit only security findings with a plausible exploit path, or say no exploitable issue was found.

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

3. **Pass 2: Exploit validation**
   For each candidate, emit a finding only if all gates pass:
   - Attacker capability is realistic for this deployment.
   - Attacker-controlled input reaches the code path.
   - A trust boundary is crossed or a security invariant is weakened.
   - A vulnerable sink or privileged action is reachable.
   - Existing validation, sandboxing, feature flags, authz, or deployment constraints do not already block it.
   - Impact is concrete: data exposure, unauthorized action, code execution, durable prompt/tool compromise, integrity loss, availability loss, or secret leakage.
   - A minimal fix is clear.
   - File/line evidence is available.

   If any gate is missing, do not promote the candidate. Mention it only under residual risk if it is worth tracking.

4. **Severity**
   - `P0 / Critical`: unauthenticated or low-friction RCE, credential/key exfiltration, broad tenant/user data exfiltration, auth bypass for privileged actions, durable agent/tool compromise with high agency.
   - `P1 / High`: authenticated privilege escalation, scoped secret disclosure, SSRF to sensitive internal systems, injection into privileged tools, supply-chain change likely to execute attacker code.
   - `P2 / Medium`: meaningful security invariant weakening with narrower reach, DoS with realistic cost, unsafe LLM/tool behavior requiring specific conditions, missing validation on sensitive but non-critical paths.
   - `P3 / Low`: defense-in-depth gap with a credible but limited path, logging/audit weakness, hardening issue that does not currently expose sensitive impact.

   Do not assign P0-P2 without a concrete exploit path. Do not inflate severity for theoretical misuse.

## Output

Lead with findings ordered by severity. Use this schema:

```markdown
- [P1] Imperative title under 80 chars
  - Location: path/to/file.ext:123
  - Problem: What security invariant is broken.
  - Exploit path: Attacker input -> trust boundary -> vulnerable sink -> impact.
  - Suggested fix: Minimal safe change.
```

After findings, include:

- **Residual risk**: gated candidates, uncertainty, or follow-up checks that did not meet finding gates.
- **Checks run**: commands or code paths inspected.

If no findings pass the gates, say so explicitly and name the highest-risk surfaces inspected.

## Guardrails

- Do not output generic checklist results as findings.
- Do not recommend broad rewrites when a narrow guard, validation, permission check, dependency pin, sandbox, or output encoding fix closes the path.
- Do not expose secrets discovered during review; identify the file/path and remediation class only.
- Do not run exploit payloads against live services unless the operator explicitly asks and the target is isolated.
- Do not rewrite historical records to remove leaked data; append remediation notes and rotate/revoke secrets instead.
