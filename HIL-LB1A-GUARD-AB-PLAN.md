# HIL-LB1a minimal guard experiment plan

Status: proposed task-local experiment only; no production/default change made.

## Source-grounded behavior

The isolated orchestrator source is commit `f45dfb243d96a7468c16e81332934223772edc56`. In `src/llm_primitives/inference.py`, the streaming branch derives `_rep_guard_active` as the inverse of `_request_is_grammar_constrained(request)` and checks accumulated output every 50 chunks (around lines 1601–1620). The same module's `_request_constraints` currently records schema, grammar and structured response format for the tap. The live controlled request had no such constraints yet contained explicitly requested repeated structure; a global default change would affect ordinary unconstrained requests without evidence about their safe operating region.

## Narrow A/B

Add a request-local, explicit opt-out field (for example `allow_repetitive_output: true`) that disables this streaming guard only for that request. Default absent/false preserves current behavior. The field must be validated as a strict boolean, flow through the actual request object, and be recorded in the tap alongside the existing constraints. Do not change grammar/schema behavior or the global default.

Run the same fixed prompt/model/runtime/seed/request cap twice: A with the current default guard, B with only the explicit opt-out. Keep native chunk sequence, stop reason, raw response and parse result. Verify A reproduces a guard stop, B either completes parseable output or stops for an independently recorded reason, and the server/owned-child cleanup remains correct. Add model-free behavior controls for absent/false/default, explicit true, invalid types, grammar-constrained requests, and unrelated request isolation. An A/B that merely disables the guard but still truncates or fails JSON is not a fix.

The Locals `TOOLS` profile also fired on the exact-tokenizer prefix at token 97, so it is not an acceptable replacement in this one case. Do not switch global defaults to it. The historical tap's 16 apparent final-chunk events remain unlabelled as live cuts because their request constraint flags were never recorded; no prevalence or historical relabeling claim follows from this single controlled result.
