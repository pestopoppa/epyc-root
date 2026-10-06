# HG-9 detect-to-fix recommendation topology

**Status:** design option only; no selector, routing activation, model call, or incumbent change. Prepared against ROOT `4c0c653baf1654c8c25c66433cf39c8faefd8e52` and epyc-orchestrator `62db79be0bf9a4cdc8341ec48d8d240a14458288`. This specification records source-backed candidates and decision boundaries; it is not evidence that a detector pool or fixer is currently wired.

**Task source:** ROOT [`reviewer-escalation-and-human-gate-policy.md`](../../handoffs/active/reviewer-escalation-and-human-gate-policy.md), HG-9 at lines 39–52 and MAIN-reviewed JEV refinement at lines 76–82. HG-9 Step 1 is no-inference; EV-13b and judge-stable scoring gate Step 2; P-AB-1 and LB-6 gate Step 3. ROOT [`tri-role-coordinator-architecture.md`](../../handoffs/active/tri-role-coordinator-architecture.md), TR-4.4 at line 101 and its decision at lines 240–247, explicitly keeps verifier-acceptance termination parallel to review/escalation.

## Source-backed present topology

The app role catalog and route map are in epyc-orchestrator `src/roles.py` at the pinned source revision. The `Tier.C` roles that the source both defines as roles and maps in `_ESCALATION_MAP` are:

| Role id | Source-backed function | Current escalation edge | Topology note |
|---|---|---|---|
| `worker_general` | General-purpose worker | `coder_escalation` | Candidate general detector role id; source does not label its model small. |
| `worker_math` | Math/property/invariant work | `coder_escalation` | Domain-specific candidate, not a universal detector. |
| `worker_summarize` | Summarization | `coder_escalation` | Domain-specific candidate. |
| `worker_vision` | Vision-language work | `coder_escalation` | Domain-specific candidate. |
| `toolrunner` | Tool execution / tool-result processing | `coder_escalation` | Candidate only for findings about tool output; not a generic reviewer. |
| `vision_escalation` | Alias of `worker_vision` | No independent edge in `_ESCALATION_MAP` | Same process/weights; do not count as an independent detector. |

The proposed general/text detector candidate set is `worker_general`, `worker_math`, and `worker_summarize`; include `worker_vision` only for vision-derived findings and `toolrunner` only for findings about tool outputs. These are valid role identifiers, not verified “small” models. The model-registry entries at this pin give `worker_general` and `worker_math` 35.2 GB, `worker_summarize` 37 GB, `worker_vision` 17.3 GB; they do not provide a small-model threshold or evidence that these models satisfy that task premise. The model registry describes `architect_general` as a 90 GB Flash-Next model entry, so it is the source-backed *candidate* larger fixer target by registered memory footprint, not measured quality. `coder_escalation` is a 27.05 GB alias on `architect_critic` and is an existing intermediate route, not the proposed larger fixer target. The exact path example remains `worker_general → coder_escalation → architect_general`; the separate finding-emitted trigger is not currently implemented.

The shared role map gives the example path `worker_general → coder_escalation → architect_general`; `worker_math`, `worker_summarize`, `worker_vision`, and `toolrunner` also map first to `coder_escalation`; `frontdoor → coder_escalation → architect_general`; `architect_general` is terminal. These are topology examples from `src/roles.py::_ESCALATION_MAP` and `get_escalation_chain`, not a claim that an emitted finding currently invokes that route. `EscalationPolicy.decide()` in `src/orchestration/escalation.py` currently receives failure/error/retry context, so a finding event is not a current `EscalationContext` event. An implementation must add no competing route framework and must not disguise a finding as a model failure.

The “small-model pool” premise is not currently demonstrated by role naming. In the pinned app `orchestration/model_registry.yaml`, worker model descriptions identify `worker_general`, `worker_math`, and `worker_summarize` with Qwen3.6-35B-A3B and `worker_vision` with Qwen3-VL-30B-A3B; `vision_escalation` is explicitly an alias. `worker_fast`/`worker_explore` are deprecated aliases, not independent live role IDs. Thus the IDs above are **valid topology candidates**, not a verified small-model detector pool. The map carries no source-backed model-size threshold; do not label a candidate “small” or claim a size ordering for fixer selection. A future owner must bind detector/fixer model eligibility to current role/model metadata before this design can become an offered menu.

**Pinned app source references at epyc-orchestrator `62db79be0bf9a4cdc8341ec48d8d240a14458288`:**

- Role identifiers, tiers, aliases, escalation map and chain: [`src/roles.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/roles.py) lines 202–255, 316–322, 406–417, 518–573, 675–705.
- Existing escalation outcomes and error-oriented context: [`src/orchestration/escalation.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/orchestration/escalation.py) lines 63–108 and 227 onward.
- Review/evidence shape: [`orchestration/review_decision.schema.json`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/orchestration/review_decision.schema.json); grounding reducer: [`src/proactive_delegation/policy_reducer.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/proactive_delegation/policy_reducer.py); envelope binding: [`src/proactive_delegation/review_envelope.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/proactive_delegation/review_envelope.py) and [`orchestration/machine_review_envelope.schema.json`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/orchestration/machine_review_envelope.schema.json). Typed question constraints: [`src/typed_decisions/types.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/typed_decisions/types.py); host action checks: [`src/typed_decisions/prepared_action.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/typed_decisions/prepared_action.py); stage accounting: [`src/typed_decisions/call_recorder.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/src/typed_decisions/call_recorder.py). These are source references only; no runtime behavior is activated.
- Current worker/vision model and alias data: [`orchestration/model_registry.yaml`](https://github.com/pestopoppa/epyc-orchestrator/blob/62db79be0bf9a4cdc8341ec48d8d240a14458288/orchestration/model_registry.yaml) lines 2395–2425, 2463–2493, 2508–2522, 2590–2604, 2662–2679, 2721–2745. The registry text is descriptive current source at that pinned commit; no live server or model state was checked.

## Finding and freshness contract

Reuse the existing app review artifact rather than inventing a parallel finding schema:

- `orchestration/review_decision.schema.json` defines a `ReviewDecision`; its `blocking.blocking_issues[]` are hard-stop issues, and `$defs.issue` includes `criterion_id`, `evidence_ref`, `remediation_target`, and `unsupported`. Top-level `evidence[]` carries typed evidence kinds and references.
- `src/proactive_delegation/review_service.py` composes review decisions and preserves evidence. `src/proactive_delegation/policy_reducer.py` defines `OBJECTIVE_EVIDENCE_KINDS = {gate_result, test_result, scorer_result}` and derives `grounded_blocking` from review evidence or the supported review-object formats. In mapping inputs it currently regards a nonempty issue `evidence_ref` as a grounding signal. That reducer signal is not itself a proof that the string resolves to a current evidence record.
- Therefore, for this proposed HG-9 option, the host-side trigger is deliberately stricter than merely “a field is present”: first accept the existing reducer’s `grounded_blocking` result; then require the triggering issue’s `evidence_ref` to resolve to a unique item in the same `ReviewDecision.evidence[]`, whose evidence kind is one of the reducer’s objective kinds, and require the review to bind to current source/candidate/prompt/pipeline/schema inputs. If any link is missing or ambiguous, do not send the finding to the fixer. This is a proposed adapter boundary, not new reducer behavior.
- Where the finding carries a machine-review envelope, use `orchestration/machine_review_envelope.schema.json` and `src/proactive_delegation/review_envelope.py::check_binding` to verify the current binding. The binding covers source and candidate hashes/versions, reviewer metadata, prompt-bundle hash, pipeline version and review-schema version. A mismatch means stale. This spec does not assert that every existing `ReviewDecision` already carries such an envelope; the packet must include a valid current envelope reference or be treated as unbound.

A finding handed to the next stage is the tuple `(decision_id, issue_index, evidence_ref, current_binding_digest)`. The fixer receives only this bound issue packet and its permitted context; it returns a repair recommendation for the owning worker/author. It does not receive permission to write or execute a patch. Any generated patch remains outside HG-9 Step 1 and needs existing host review/authorization.

## Documentation-only option shape

The following JSON is a **specification example**, not an application config, JSON Schema registration, selector input, or runtime-accepted object. It gives AutoPilot a structured option shape that a later approved mutation/evaluation path could represent without baking a fixed pipeline into code.

```json
{
  "schema_version": "hg9.detect_repair_topology.v1",
  "detector_pool": ["worker_general", "worker_math", "worker_summarize"],
  "finding_contract": {
    "decision_schema": "orchestration/review_decision.schema.json",
    "issue_pointer": "/blocking/blocking_issues/*",
    "evidence_pointer": "/evidence/*",
    "issue_evidence_ref_field": "evidence_ref",
    "required_grounding": ["reducer.grounded_blocking", "resolved_objective_evidence_ref"],
    "current_binding": "orchestration/machine_review_envelope.schema.json"
  },
  "trigger": "current_grounded_finding_emitted",
  "fixer_role": "architect_general",
  "route_surface": "EscalationPolicy",
  "stage_order": ["detect", "recommend_fix"],
  "fallback": "incumbent_route",
  "cost_attribution": ["detector", "fix_recommendation"]
}
```

`detector_pool` values above are the source-valid general/text role candidates only; modality- or tool-specific roles are omitted from this generic example. The pinned registry does not qualify them as small models, so the “small-model detector” premise remains unverified. `architect_general` is the explicit fixer-role candidate because its model-registry entry has a larger memory footprint (90 GB) than the worker candidates; this is not a quality claim. `route_surface` names existing routing to map, but no claim is made that `EscalationPolicy` already consumes `current_grounded_finding_emitted`. The checker/routing owner must decide later how the option maps through this existing surface without changing current behavior.

## Deterministic statuses and incumbent fallback

Every non-accepted detector-to-fixer transition leaves the incumbent path unchanged. Record one of these reasons; do not silently drop a finding, invent a route, or rewrite absent telemetry as zero:

| Status | Synthetic condition | Step 1 option result |
|---|---|---|
| `invalid_finding` | Current typed output is malformed/schema-invalid and no recovered valid decision is available | No fixer stage; preserve the failure and incumbent route. A prior retry failure alone does not invalidate a recovered decision. |
| `empty_findings` | Valid decision with no blocking issues | No fixer stage; incumbent route. |
| `unresolved_evidence_ref` | `evidence_ref` missing, ambiguous, unsupported, or does not resolve in the evidence array | No fixer stage; incumbent route. |
| `stale_finding` | Binding no longer matches source/candidate/prompt/pipeline/schema | No fixer stage; incumbent route. |
| `no_eligible_fixer` | Host menu has no eligible role | No fixer stage; incumbent route. |
| `menu_changed` | Current offered role catalogue differs from prepared menu | Host `validate_prepared_action` returns `stale`; incumbent fallback. |
| `fixer_unavailable` | Offered fixer is unavailable at dispatch | Host validation returns `model_unavailable`; incumbent fallback. |
| `not_authorized` | Host authorization is false | Host validation returns `unauthorized`; incumbent fallback. |
| `accepted` | Valid current finding, resolved objective evidence, unchanged menu/revision, eligible and available authorized fixer | Only a later enabled shadow/approved option may request a recommendation; no execution authority. |

For a later menu choice, reuse `Question(CHOICE)` and `DecisionResult` for bounded role/rubric IDs only; `CHOICE` requires at least two unique options. If exactly one eligible fixer remains, the host maps that role deterministically without constructing a model choice question; zero eligible roles follows `no_eligible_fixer`. Reuse `prepare_action` / `validate_prepared_action` for current menu, revision, read-set, expiry, authorization and availability checks. `PreparedAction` validation supplies incumbent fallback for rejection; it is not evidence that the finding is correct or permission to apply a patch. On invalid typed output, preserve the explicit parse failure and incumbent behavior.

## Stage order and accounting

The dependency is serial: detector completes and produces the bound finding before the fixer receives it. Do not represent the two calls as independent heads over one state. Existing `src/typed_decisions/call_recorder.py::record_llm_calls` is the per-stage accounting seam. A future mocked or shadow integration should record detector and fix-recommendation calls separately and carry missing token/time fields as `None`. Do not add a new cost schema, fill unknowns with zero, or claim an accuracy/F1/cost result from these fixtures.

## Mocked boundary-case specification (not executed)

These nine cases are concrete acceptance inputs/outcomes for a future focused, offline synthetic CI target. They test only the host mapping contract. Fixtures use synthetic IDs, hashes, roles and evidence; they are **not executed tests, model-quality evidence, or proof of runtime routing**.

| # | Synthetic input | Expected outcome |
|---|---|---|
| 1. Valid grounded finding | Decision `rev-001`; issue 0 has `criterion_id="C-1"`, `evidence_ref="ev-01"`, `unsupported=false`; `evidence=[{kind:"test_result",ref:"ev-01"}]`; current envelope binding hashes match; role menu offers `architect_general`. | Trigger is `current_grounded_finding_emitted`; packet is `(rev-001,0,ev-01,<current digest>)`; detector completes before fixer receives packet. No patch is applied. |
| 2. Invalid and recovered typed output | If current output `{"answers":{}}` omits the required `review_decision` answer, it produces `ParseFailure(reason="invalid_value", detail="question 'review_decision': missing answer")`; with no recovery, return `invalid_finding` and preserve incumbent. If attempt 1 instead has `ParseFailure(reason="no_json", detail="attempt 1/2: no balanced JSON object found")` and attempt 2 yields a valid `review_decision` with unique current objective evidence and matching envelope, use the recovered decision after grounding/binding checks and preserve retry history/cost. | Unrecovered current failure means no fixer call; recovered valid result is not rejected solely because `DecisionResult.failures` is nonempty. |
| 3. Empty findings | Valid `ReviewDecision` has `blocking={tripwire:false,blocking_issues:[]}` and no issue pointers. | Status `empty_findings`; no fixer call; incumbent path unchanged. |
| 4. Unresolved evidence | Issue has `evidence_ref="ev-missing"`, while evidence contains only `{kind:"test_result",ref:"ev-other"}`. | Status `unresolved_evidence_ref`; do not rely on reducer's nonempty-string grounding alone; no fixer call; incumbent path unchanged. |
| 5. Stale binding | Valid issue/evidence, but prepared envelope binds candidate hash `sha256:0000000000000000000000000000000000000000000000000000000000000000`; current candidate hash is `sha256:1111111111111111111111111111111111111111111111111111111111111111`. | Existing `check_binding` reports changed candidate binding; status `stale_finding`; no fixer call; incumbent path unchanged. |
| 6. Changed role menu | Prepare with offered choices `["coder_escalation","architect_general"]`; before dispatch current menu is `["architect_general"]`; selected role is `coder_escalation`. | `validate_prepared_action` returns `stale` with `fallback="incumbent_fallback"`; status `menu_changed`; no dispatch. |
| 7. No eligible fixer | Valid grounded issue; host-filtered fixer menu is `[]`. | Status `no_eligible_fixer`; no choice question/call; incumbent path unchanged. |
| 8. Fixer unavailable / unauthorized | Valid prepared menu includes `architect_general`; first fixture has `model_available=false`, second has `authorized=false`. | Respect host validator: `model_unavailable` or `unauthorized`, each with incumbent fallback; no call or patch execution. |
| 9. Stage attribution and TR-4.4 separation | Fake recorder returns detector `{tokens:12,prompt_ms:null}` and fixer `{tokens:null,prompt_ms:5}`; separate trace marker records detector completion; a separate synthetic TR-4.4 `ACCEPT` arrives without a finding. | Preserve separate call rows and nulls; enforce detect-before-fix; TR-4.4 alone does not trigger fix recommendation, and HG-9 finding alone does not implement verifier early termination. |

## Gates, owner and scope

This note completes only the non-inference design/mapping step if MAIN and the owning reviewer-control-plane session apply it. `EscalationPolicy`/role-chain ownership belongs to app orchestration owners; typed-choice/prepared-action details belong to the typed-decision host owners. Keep this work documentation-only. Any later selector code needs separate AutoPilot/D9 owner review, EV-13b resume plus judge-stable Step 2 F1 evaluation, and Step 3 paired fix-acceptance/cost comparison under P-AB-1 and LB-6. TR-4.4 remains independent and parallel.

**Scope grade:** LOW for this source-linked design note and contract mapping; MAIN accepted 2026-10-06 for documentation scope only. Runtime routing and repair recommendation are out of scope. Main residual risks are: no role currently establishes the task’s “small model” requirement; the existing reducer’s `evidence_ref` heuristic is not a reference-resolution check; route code has no finding-emitted trigger; and static fixtures do not prove model quality, runtime dispatch or patch safety.
