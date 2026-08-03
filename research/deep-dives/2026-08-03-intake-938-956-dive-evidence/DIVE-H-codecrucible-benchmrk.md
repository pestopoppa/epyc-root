# DIVE-H — CodeCrucible (943) + benchmrk (948)

## THE OVERTURN: codecrucible RUNS ON LOCAL MODELS. Documented, not incidental.
internal/cli/scan_helpers.go:56-64 ships TWO first-class local providers:
  "ollama":        baseURL http://localhost:11434, authRequired:false, wireProvider:"openai"
  "openai-compat": authRequired:false, wireProvider:"openai", no default baseURL (--base-url mandatory)
wireProvider "openai" routes to baseURL + "/v1/chat/completions" (client.go:348-349)
= byte-for-byte what llama-server exposes. Documented at README.md:127,131-141.
phase.go:36-38 states the intent: "BaseURL overrides the hardcoded per-provider default. Use for
proxies, Azure OpenAI, Vertex-vs-AI-Studio, local mock servers."
=> intake-943's OWN stated condition for adopt_component IS MET. verdict adopt_patterns -> adopt_component.

Working invocation:
  codecrucible scan <repo> --provider openai-compat --base-url http://localhost:8080 \
    --model <served-name> --context-limit 131072 --max-output-tokens 8192 \
    --prompts-dir prompts/exploit-proof-web-python --max-cost 0 --output /tmp/cc.sarif

Three things make it land cleanly:
- PER-PHASE heterogeneity is FREE (phase.go:117-197): provider/model/base-url/key resolved
  independently per phase w/ analysis->{feature-detection,audit} inheritance. We can run analysis
  on local GGUF and audit on a metered model, or the reverse. THAT IS the cost-aware-routing ablation.
- Unknown models degrade safely (phase.go:311-324): 128K ctx / 8192 out defaults + per-phase override.
- Client SELF-HEALS against non-conforming servers (client.go:264-307): learns and latches forced
  tool_choice, temperature, max_tokens->max_completion_tokens — exactly llama-server's divergence class.
Frictions (non-blocking): pricing assumes per-M rates so set --max-cost 0 or register a zero-price
model; tokenizerSafetyMargin=0.20 (scan.go:496) is Anthropic-BPE-calibrated, a guess for GGUF.

## THRESHOLD RESOLVED — AND IT IS NEARLY INERT
audit-confidence-threshold default **0.3** (config.go:160); batch 25; max-cost $25.
BUT the prompt's own scale (audit.yaml:211-217) is REJECTED <0.50, CONFIRMED >=0.70, and
applyAuditVerdicts drops on `verdict=="rejected" || confidence<threshold` (scan_audit.go:403).
The model self-assigns the verdict token at its own 0.50 boundary => the numeric 0.3 gate almost
never bites. **If we lift "their threshold" we lift a no-op. Lift the PROMPT bands instead.**

## THE AUDIT PROMPT CARRIES ITS OWN NEGATIVE RESULT (highest-value liftable artifact)
prompts/default/audit.yaml:5-13 records the measurement that forced the rewrite:
  "rejected=0 across all runs. The audit added findings (42->47) and declared 'no false positives'
   while the annotation set disagreed on 14 of them. Two structural causes: 1. No null hypothesis.
   CONFIRMED was the default... 2. 'Report any NEW findings' turned the filter into a second
   discovery pass."
Fix = a four-gate ORDERING our eight gates do not encode:
- GATE 0 PRODUCTION REACHABILITY (:58-116) runs BEFORE gates 1-3 and SHORT-CIRCUITS. Explicit null
  hypothesis: "the finding is non-production. You must DISPROVE this to proceed. 'It's in a .go file,
  not a _test.go file' is not disproof." 3 sub-gates + rebuttability clause.
- GATE 1/2/3 reachability / absence-of-mitigation / material impact (:28-46). Mitigation gate demands
  "you must name the location where the mitigation WOULD be if it existed, and state it is absent there."
- MANDATORY PRE-CONFIRM REFUTATION (:49-52): "BEFORE issuing CONFIRMED... write down the strongest
  case AGAINST it... If you cannot refute it, you cannot confirm the finding."
- ANTI-ANCHORING AT THE DATA LAYER, not just prose (scan_audit.go:92-106): field renamed
  `unverified_exploit_sketch`, payload wrapped `{"claims_to_verify":[...]}`. Prompt then says hedges
  like "is not exploitable" are HYPOTHESES TO VERIFY: "'The finding itself acknowledges it is not
  exploitable' is never a valid REJECTED reason on its own."
  => this PRE-EMPTS the intake-875 de-anchoring recommendation, and de-anchors in BOTH directions.

## TWO STRUCTURAL FALSE-REJECT MITIGATIONS (the only bound on intake-836's failure mode)
- SYMMETRIC-SKEPTICISM GATE (scan_audit.go:377-385): a `rejected` verdict with EMPTY blocking_code is
  coerced to `unverified`, logged, and the finding SURVIVES — "multi-file invariants routinely get
  rejected here just because the auditor couldn't re-prove the whole chain in one pass."
  Rejection must cite a quoted source line; assertion alone is not enough.
- THREE-VALUED OUTCOME (:390-399): `unverified` retained, confidence FLOORED at threshold so a low
  score cannot re-drop it, prefixed "[UNVERIFIED - audit could not re-prove the full chain; treat as
  a lead]". A live instance of reviewer-decision-plane.md's three-valued outcome.
- Plus two fail-open biases same direction: no-matching-verdict kept as-is; failed audit batch leaves
  findings unaudited but RETAINED.
=> intake-836 contradiction AMENDED: still CONFIRMED that no FR RATE is measured, but unmeasured != unmitigated.

## 14 PROMPT SETS, NOT 3
default, carlini, carlini-curated, exploit-proof + 7 language variants, nano-analyzer (PROMPT_SETS.md:31-45)
cwe_deep_analysis.yaml = 58KB, 30 CWEs, uniform schema {title, analysis_prompt, validation_checks[],
false_positive_indicators[]}, spliced per-finding at audit time (scan_audit.go:154-190). Header records
the calibration lesson: previous FP indicators "were too exotic to fire (row-level security, HMAC'd
tokens) while the actual FPs were mundane (framework defaults, duplicate manifestations, hardening-vs-vuln)".

## DEDUP: LIFT THE ORDERING FROM ONE REPO, THE KEY FROM THE OTHER
codecrucible dedup = (fileURI, startLine, CWE) highest-severity-wins (postprocess.go:63-98), ordered
BEFORE the audit (scan.go:784 -> 787 -> 815). CONFIRMED.
BUT it is anchored on startLine EQUALITY — no range overlap, no CWE-equivalence. Findings at 88-166
and 90-166 with the same CWE BOTH survive.
benchmrk's matcher is strictly better -> use rangeDistance + cwe.Distance as the key.

## benchmrk MATCHER (the liftable asset; ~24KB tested Go)
- Location = RANGE OVERLAP not line-exact (matcher.go:326-334); missing EndLine collapses to StartLine
- Path normalization strips container mounts /target/ /src/ /app/; unique-suffix fallback,
  AMBIGUITY -> NO MATCH (:439-501)
- CWE = MITRE-HIERARCHY DISTANCE not string equality (cwe/cwe.go:83-127): 0 identical; 1 direct
  parent/child or curated pair; 2 siblings/two hops/shared category; 3+ common ancestor; -1 unrelated.
  **PILLARS EXCLUDED as meeting points** (:180-192) — "everything is under a pillar, so meeting there
  is noise." Curated mechanism<->consequence list (:208-236): 915->269, 347->287, 620->352, 862->{863,639}, 328->327.
- FIVE TIERS: exact 1.0 / hierarchy 0.95-0.75 / fuzzy 0.9->0.5 (<=5 lines) / category 0.5->0.3
  (<=20 lines, CWE-related REQUIRED) / same_line 0.2
- STRICT 1-to-1 GREEDY, sort.SliceStable + startGap then lower-ID tiebreaks (:181-222) — comment records
  that sort.Slice's INSTABILITY made assignment sensitive to unrelated changes. DETERMINISTIC BY
  CONSTRUCTION = load-bearing for replay under our measurement constitution.
- CWE SETS not single CWEs: best distance over the whole set (:262-278)
- GROUP PROPAGATION (:378-429): annotations sharing a group with a matched one get synthesized
  match_type='group' rows at 0.4 — one consolidated IDOR finding scores TP across every endpoint.
- FP ATTRIBUTION (metrics.go:220-276): TP = matched a status:valid; **FP = matched a status:INVALID
  decoy OR matched nothing**; FN = valid unmatched; TN = invalid unmatched; needs_review counts FP.
- VULNERABILITY-LEVEL counting: a vuln with 6 evidence rows, 1 matched = ONE TP, not six.
- THE DUAL-GOLD MECHANISM IS status:"invalid" DECOYS. Without them precision is unmeasurable.

## THE IMPORTABLE ENVELOPE (adopt as our dual-gold label schema) — vulns.go:15-71
{"vulnerabilities":[{"name","description","criticality":"must|should|may","status":"valid|invalid|disputed",
 "cwes":["CWE-639","CWE-862"],  # a SET, any one matches
 "annotated_by":["alice","bob"], # len() IS the consensus level
 "evidence":[{"file","line","end","role","category","severity"}]}]}
Import guardrails worth copying (vulns.go:86-120): duplicate names rejected; re-import without
--replace blocked because the second copy is "a permanent phantom FN" that silently halves recall.

## benchmrk CORPUS: IT NEVER EXISTED
404 on all 4 cited paths; absent on ALL THREE branches; 0 tags, 0 releases, 8 commits.
Commit 18c4c582 claims "align defaults with bundled corpus" but its diff touches ONLY
examples/quick-run.sh. Referenced from FIVE files in THREE different paths, and
examples/quick-run.sh:43 sets it as the EXECUTABLE DEFAULT — the shipped quickstart is broken
out of the box. This is a checklist-omission defect of exactly the class our own W7 work names.

## OTHER CORRECTIONS
- Claim "confidence-interval overlap test" DOWNGRADED to PARTIAL: it is a +-1 sigma
  interval-intersection HEURISTIC (cmd/benchmrk/analyze.go:558-567), not a CI, not a significance
  test. Do NOT inherit the framing into scoring-infra-standardization.md.
- SKILLS.md/AGENTS.md have NO LLM-scanner path. The path is the generic local-wrapper contract
  (SKILLS.md:166-227): SARIF 2.1.0 to $OUTPUT_DIR/results.sarif, minimal env, docker --network none.
  **Since codecrucible EMITS SARIF, a three-line wrapper makes it a first-class benchmrk scanner.
  The two repos compose without either knowing about the other.**
- ai-annotation-prompt.md is a complete LLM-ASSISTED GROUND-TRUTH AUTHORING PROMPT incl. an explicit
  instruction to author status:"invalid" decoys — the recipe for the corpus benchmrk does not ship.

## ENTRY DISPOSITIONS
943 -> dive-verified, VERDICT CHANGES adopt_patterns -> adopt_component
948 -> dive-verified, adopt_component stands, novelty high stands

## LEDGER: 16 drafts, 3 declines (full text in the agent transcript)
Owners: security-review-skill.md (x5), reviewer-decision-plane.md, reviewer-control-plane-index.md (x3),
reviewer-calibration-accounting.md (x2), eval-tower-verification.md (x3),
scoring-infra-standardization.md, reviewer-typed-artifacts.md
Declines: SARIF-as-interchange (fold into #11), import-graph chunker (solves a problem we don't have),
report the dangling-corpus defect upstream (commits us to an external interaction not sanctioned)
