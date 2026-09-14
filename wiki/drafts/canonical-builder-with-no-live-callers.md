# A canonical builder that no live writer calls (embedding-convention drift)

**Category**: `memory_augmented`
**Confidence**: verified (local code + unit tests, zero inference)
**Date**: 2026-09-14
**Source**: RTG-15 EPD-3-R2/R3, `epyc-orchestrator` `9096a600`; handoff
`handoffs/active/learned-routing-controller.md`
**Folds into**: [Memory-Augmented Models](../memory-augmented.md) — episodic-store integrity, next
to the FAISS/id_map desync note

## The mechanism

A 2026-07-27 audit found the episodic store carried at least four embedding conventions, so the
vector encoded *which writer produced the row* (writer-path ROW-AUC 0.906–0.940). The remedy was a
single canonical builder, `MemoryRecord.embedding_text()`, plus a reseed of the whole corpus onto it.
That worked: the store is on the canonical format.

It did not hold, because **the canonical builder had no live callers.** It was reached only by the
reseed tool and the degeneracy guard — both offline. All three writers that run in production
re-spelled the convention in their own words, and each had already drifted from it:

| Writer | Drift as of `origin/main` |
|---|---|
| `embedder.TaskEmbedder._serialize_task_ir:243` | keyed on field PRESENCE not truthiness (a TaskIR with `priority: None` emitted the literal `priority:None`); no `.strip()`; no 2000-char cap; extra `constraints:` / `input_types:` segments |
| `scripts/benchmark/seeding_injection._precompute_embedding:65` | hard-coded `type:chat` for every suite, so a `math`/`coder`/`hotpotqa` row's vector described a convention its own stored context contradicted |
| `orchestration/repl_memory/seed_loader.py:470` | embedded the raw task string with no prefix at all — the shape all 94 post-reseed `seed` rows carry |

So the store's format was correct only between a reseed and the next write, and the *next* reseed
would have re-published the drift as the new canonical corpus. The format was clean; the process
that produces it was not.

## Why a format test cannot catch this

The pre-existing convention test (`tests/unit/test_memory_record.py:89`) compares two
`MemoryRecord`s with identical fields. That is a property of the builder, and every writer that
bypasses the builder passes it trivially. The same shape of hole appeared one box earlier in the same
handoff (EPD-3-R4): the standing integrity gate hand-built `type:{t} | objective:{o}` for its
self-match probe and so spent margin cosine-ing stored vectors against a string that was never
embedded.

## The rule

**A canonical builder is only canonical if the live write path calls it.** Two enforcement layers,
both cheap, and the second is the one that lasts:

1. **Golden**, pinned to the *corpus*, not to the code: build each writer's text for a stored row
   lifted verbatim out of the live store and assert equality with
   `record_from_legacy_context(stored_context).embedding_text()`. A golden captured from the builder
   alone proves the writers agree with each other, not with what was published.
2. **Delegation guard**: monkeypatch the canonical builder and assert each writer entry point
   *calls* it. Output equality is necessary but not sufficient — a re-spelling that happens to agree
   today passes every golden and drifts on the next edit. Assert about the call, not the string.

Corollary for query paths: `_serialize_task_ir` is both a write and a **query** serializer, so a
drift there does not merely mislabel new rows — it makes live queries search a different convention
than the corpus was published in, silently costing recall with no error anywhere.

## Cross-reference

`priority` is still in the canonical text and still leaks the writer path (45.4% of rows carry it).
Dropping it is EPD-3-R1 and is gated on an inference window: the recipe change and the re-embed must
flip together, or live queries mismatch 100% of the store instead of today's 45.4%.
