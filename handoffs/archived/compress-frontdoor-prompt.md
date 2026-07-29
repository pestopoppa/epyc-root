# Handoff: Compress frontdoor.md TaskIR Prompt

**Created**: 2026-02-09
**Priority**: Medium (latency optimization, not correctness)
**Blocked by**: Nothing — ready to implement

## Context

The `orchestration/prompts/frontdoor.md` system prompt (~2000 tokens) is sent to the Qwen3-Coder-30B-A3B frontdoor on every TaskIR generation request. Two full JSON examples (~800 tokens combined) dominate the prompt. At 18 t/s frontdoor speed, the prompt eval cost is noticeable (~4s) but not as severe as the REPL prompt was (which we just compressed 88% via COMPACT_ROOT_LM_TOOLS).

The frontdoor prompt is only used for TaskIR emission, NOT for REPL mode. REPL mode now uses MINIMAL style with compact tools.

## Current Structure (orchestration/prompts/frontdoor.md)

```
Lines 1-8:    Role description (~50 tokens)
Lines 10-15:  Output requirements (~40 tokens)
Lines 17-22:  "Do NOT" constraints (~30 tokens)
Lines 24-39:  Available agent roles table (~120 tokens)
Lines 41-87:  Full TaskIR JSON schema (~350 tokens)
Lines 89-99:  Routing guidelines table (~80 tokens)
Lines 101-113: Gate selection (~60 tokens)
Lines 115-119: Escalation rules (~40 tokens)
Lines 121-185: TWO FULL JSON EXAMPLES (~800 tokens)  ← TARGET
Lines 187-193: Remember section (~30 tokens)
```

**Total**: ~1600 tokens. Examples are ~50% of the prompt.

## Plan of Action

### Phase 1: Measure baseline (mandatory before changes)

```bash
# Count current token estimate
python3 -c "
text = open('orchestration/prompts/frontdoor.md').read()
print(f'Chars: {len(text)}, Est tokens: {len(text)//4}')
"

# Run 3 TaskIR generations with current prompt, record timing
# Use the seeding infra or a manual curl to port 8080
```

### Phase 2: Compress the examples

**Strategy**: Replace 2 full examples with 1 minimal skeleton + field annotations.

Current examples are 62 lines of JSON. Replace with:

```json
// Example: "Add error handling to registry loader"
{"task_id":"a1b2","task_type":"code","priority":"interactive",
 "objective":"Add try/except to RegistryLoader",
 "agents":[{"tier":"B","role":"coder"}],
 "plan":{"steps":[
   {"id":"S1","actor":"coder","action":"Add error handling","outputs":["src/registry_loader.py"]},
   {"id":"S2","actor":"worker","action":"Write tests","depends_on":["S1"],"run_gates":true}
 ]},
 "gates":["format","lint","unit"],
 "definition_of_done":["Error paths have try/except","Tests cover error cases"],
 "escalation":{"max_level":"B3","on_second_failure":true}}
```

This is ~12 lines vs ~35 lines for the code example alone. Drop the summarization example entirely — it just reinforces the same schema.

**Estimated reduction**: ~800 tokens → ~200 tokens = **75% example reduction**, ~1600 → ~1000 total = **38% overall**.

### Phase 3: Compress the schema section

The full JSON schema (lines 41-87) repeats information the model sees in the example. Compress to a field reference table:

```
## TaskIR Fields (all required unless noted)
task_id, created_at, task_type (chat|doc|code|ingest|manage), priority (interactive|batch)
objective: clear success statement
context: {conversation_id?, prior_task_ids[], relevant_files[], notes?}
inputs: [{type: path|url|text|image|audio, value, label?}]
constraints[], assumptions[]
agents: [{tier: B|C, role, model_hint?}]
plan.steps: [{id, actor, action, inputs?, outputs?, depends_on?, run_gates?}]
plan.parallelism.max_concurrent_workers: int
gates: [schema, format, lint, typecheck?, unit?, integration?]
definition_of_done: [human-readable criteria]
escalation: {max_level: B1|B2|B3, on_second_failure: bool}
```

**Estimated reduction**: ~350 tokens → ~120 tokens.

### Phase 4: Compress routing/gate tables

Merge routing guidelines and gate selection into a single compact table:

```
## Routing
code → coder (spec K=24) | refactor → coder+worker | ingest → ingest (NO SPEC!)
summarize → worker (lookup 12.7x) | math → math | vision → vision | architecture → architect (IR only)

Gates: always schema+format. Add lint (code/shell), typecheck (typed Python), unit (when tests produced).
```

~140 tokens → ~60 tokens.

### Phase 5: Validate

1. **Format compliance test**: Generate 10 TaskIRs with compressed prompt, validate against `orchestration/task_ir.schema.json`
2. **Diff quality**: Compare outputs with full prompt vs compressed — check field completeness
3. **Timing**: Measure prompt eval improvement (expect ~1.5s savings at 18 t/s)
4. **Regression check**: Run 3-way seeding dry run if frontdoor is in the evaluation path

### Phase 6: Hot-swap support

The frontdoor prompt is currently loaded as a static file. If the API routes read it from disk at request time (like the REPL tools_file/rules_file now do), no code changes needed — just edit the file. If it's loaded once at startup, add the same hot-swap pattern:

```python
# In whatever loads frontdoor.md:
prompt_text = Path("orchestration/prompts/frontdoor.md").read_text()
```

Check `src/api/routes/chat_pipeline/stages.py` or wherever the frontdoor system prompt is assembled.

## Expected Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Prompt size | ~1600 tokens | ~900 tokens | **-44%** |
| Prompt eval (cold) | ~4s | ~2.3s | **-43%** |
| TaskIR quality | Baseline | Same (validated) | No regression |

## Risk Assessment

- **Low risk**: The frontdoor model has seen thousands of TaskIR examples in training. One skeleton example + field reference is likely sufficient.
- **Mitigation**: Keep the full prompt as `frontdoor_verbose.md` for fallback. The hot-swap pattern means you can revert by editing one filename.
- **Do NOT compress**: The "Do NOT" constraints (lines 17-22) and the agent roles table — these prevent common failure modes.

## Files to Touch

| File | Change |
|------|--------|
| `orchestration/prompts/frontdoor.md` | Compress examples, schema, routing tables |
| `orchestration/prompts/frontdoor_verbose.md` | Backup of current full version |
| `src/api/routes/chat_pipeline/stages.py` | Verify hot-swap or add it |
| `tests/unit/test_frontdoor_prompt.py` | Optional: validate compressed prompt produces valid TaskIR structure |

## Resume Commands

```bash
# 1. Measure current baseline
wc -c orchestration/prompts/frontdoor.md
python3 -c "print(len(open('orchestration/prompts/frontdoor.md').read()) // 4, 'est tokens')"

# 2. Back up current prompt
cp orchestration/prompts/frontdoor.md orchestration/prompts/frontdoor_verbose.md

# 3. After editing, validate schema compliance
python3 orchestration/validate_ir.py task orchestration/last_task_ir.json

# 4. Run tests
pytest tests/unit/test_prompt_builders.py -v
```
