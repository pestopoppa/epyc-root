# Handoff: Prompt Lookup Integration

**Created:** 2026-01-23
**Status:** BLOCKED - Needs Investigation
**Priority:** Medium
**Goal:** Integrate prompt lookup optimization into orchestration stack for 12.7x summarization speedup

---

## Background

Track 8 (Prompt Lookup) achieved **95.18 t/s** (12.7x speedup) for summarization tasks, documented in RESULTS.md. This optimization matches n-grams from the prompt to predict tokens, highly effective when generating text that references source material.

**Current Problem:** Cannot reproduce the benchmark. The documented flag `--lookup-ngram-min 3` doesn't exist in current llama.cpp binaries.

---

## What We Tried

### 1. llama-lookup Binary (CRASHED)
```bash
/mnt/raid0/llm/llama.cpp/build/bin/llama-lookup \
  -m Qwen2.5-Coder-32B.gguf \
  -f prompt_with_source.txt \
  --draft-max 4 \
  -t 96 -c 16384 -n 500

# Result: GGML_ASSERT(src/llama-context.cpp:1008: n_tokens <= n_batch) failed
```

### 2. llama-cli with --lookup-ngram-min (INVALID FLAG)
```bash
llama-cli --lookup-ngram-min 3 ...

# Result: error: invalid argument: --lookup-ngram-min
```

---

## Investigation Needed

### llama-lookup Workflow
The llama-lookup system appears to use pre-built lookup caches:

1. **llama-lookup-create** - Build n-gram lookup cache from source text
2. **llama-lookup** - Use cache with `-lcs` (static) or `-lcd` (dynamic) flags

```bash
# Hypothesized workflow:
llama-lookup-create -m MODEL.gguf -f source.txt -o cache.bin
llama-lookup -m MODEL.gguf -lcs cache.bin -f prompt.txt -n 500
```

### Questions to Answer

1. **How was 95.18 t/s achieved?**
   - Was it a different llama.cpp version?
   - Was there a lookup cache pre-built?
   - Is `--lookup-ngram-min` a compile-time option?

2. **Does llama-lookup-create fix the issue?**
   - Test: `llama-lookup-create --help`
   - Build cache from Twyne whitepaper content
   - Use cache with llama-lookup

3. **Was this an older API?**
   - Check git history for when `--lookup-ngram-min` was added/removed
   - May need to check llama.cpp changelog

---

## Blocked Dependencies

- **llama.cpp version compatibility** - Need to identify which version has working prompt lookup
- **Lookup cache workflow** - Not documented in RESULTS.md

---

## Test Material Available

- `/mnt/raid0/llm/tmp/twyne_summarize_prompt.txt` - 10.7K character prompt with Twyne whitepaper analysis
- Qwen2.5-Coder-32B model (documented as achieving 95.18 t/s with lookup)

---

## Acceptance Criteria

1. [ ] Reproduce 95.18 t/s or comparable speedup on summarization
2. [ ] Document working command/workflow
3. [ ] Integrate into orchestrator stack for `ingest_long_context` role
4. [ ] Add to QUIRKS.md if version-specific

---

## Resume Commands

```bash
# Check llama-lookup-create usage
/mnt/raid0/llm/llama.cpp/build/bin/llama-lookup-create --help

# Check if ngram flag exists in any binary
grep -r "lookup-ngram" /mnt/raid0/llm/llama.cpp/

# Check llama.cpp commit history for lookup changes
cd /mnt/raid0/llm/llama.cpp && git log --oneline --all -- "*lookup*" | head -20
```

---

## Related Files

- `docs/reference/benchmarks/RESULTS.md` - Track 8 documentation
- `docs/reference/models/QUIRKS.md` - llama-lookup crash documented
- `progress/2026-01/2026-01-23.md` - Investigation log
