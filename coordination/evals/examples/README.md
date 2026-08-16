# Example packs — the few-shot content injected into classifier prompts

One file per decision, named `<decision>.md`, matching the `decision` field of the fixtures in
`../fixtures/`. Each pack holds clearly-labeled **positive** and **negative** examples for exactly
one choke-point classifier, written in the shape the classifier will actually see them.

This directory is where judgment heuristics live now. Under the [prose-rule
moratorium](../README.md) a heuristic that used to be written as a rule in `BUS_PROTOCOL.md` or an
agent file is written here instead, as a worked example with its verdict — because a rule is
recalled at the moment of *reading* and an example is present at the moment of *deciding*.

## The pipeline

```
incident / edge case
        │
        ▼
../fixtures/<decision>.json        labeled example, label_provenance recorded, evidence_ref
        │                          (the durable, machine-checkable record)
        ▼
<decision>.md  (this directory)    the subset chosen as few-shot demonstrations,
        │                          rendered as prompt text, each citing its fixture id
        ▼
classifier prompt at runtime       e.g. premise_screener (P2-2)
```

Fixtures are the corpus; packs are a **curated projection** of it. A pack never invents an example:
every entry cites the `id` of the fixture it came from, so a reader can trace any demonstration back
to the artifact that proves its label.

## Rules for a pack

1. **Every example cites its fixture id.** No uncited example. If it is worth showing the model, it
   is worth having a labeled fixture with an `evidence_ref` behind it.
2. **Positives and negatives are both mandatory and explicitly headed.** A pack of positives only
   teaches a classifier to say yes; the measured failure mode here is a screener that passes
   everything well-formed. Include the near-misses — the examples that *look* like the other label.
3. **`ledger-narrative` examples may appear in a pack but may never gate a promotion.** Mark them
   inline. They are demonstrations, not evidence.
4. **The example is the input the classifier sees, plus the verdict and the discriminating
   reason.** Not a rule restated as prose. If you catch yourself writing "always check whether…",
   you are writing a rule — turn it into the example that would have caught it.
5. **Keep packs short and discriminative.** Prompt budget is real. Prefer replacing a weak example
   over appending a redundant one; the fixture corpus keeps everything, the pack keeps what teaches.
6. **Balance the classes.** A pack whose examples are 90% one label teaches the prior, not the
   decision.

## Current packs

| Pack | Decision | Consumer | Fixtures |
|---|---|---|---|
| [`premise_screener.md`](premise_screener.md) | `premise_screener` | P2-2 (`worker_runner` preflight) | `../fixtures/premise_screener.json` |

New decision ⇒ new pack file plus its fixture file, and a row here.
