# M4 CPU quality evidence replay packet (preparation only)

Status: **NOT QUALIFIED / no measurement evidence**. Prepared 2026-11-04 from the current checkout. This packet carries the existing strict evidence auditor and its source test so a separate session can replay once the pre-run bindings and captures are supplied. It intentionally contains no guessed role scope or inherited GPU quality result.

## Included verifier

- `m4_quality_audit.py` SHA-256 `ee2abeef61c01e90fedc2b9af3cd4dcbefd37c8f17ccae69ae773f4d74f2d05d`
- `test_m4_quality_audit.py` SHA-256 `cce3da7ad7e8f434c346f2a82fdac6cd437d7d7d72c3034cdf531f34f81213d1`

The verifier requires an independently supplied pre-run plan digest (`epyc.m4.quality_audit_plan.v1`) and checks the plan's role/suite/question scope, model paths, prompt hashes and expected answers, runner source hash, paired baseline/candidate directories, original per-question responses, finish/error/truncation flags, and consistency of native summaries. It refuses missing, duplicated, unexpected, escaped, or mismatched records. It is a consistency auditor, not a scoring policy, quality gate, or measurement warrant.

Replay command after a reviewed packet is complete:

```sh
python3 m4_quality_audit.py --plan plan.json --plan-sha256 <independently-recorded-plan-sha256> --runs runs --output audit.json
```

Run from this directory; use a new, nonexistent output path. Exit 0 means internally complete under the pinned plan, exit 2 means incomplete/refused. This does not itself authorize a run or make a promotion decision.

## Inputs not available; therefore no CPU arm was bound

The active M4 handoff says the prior scope snapshot had 10 CPU roles and 3 GPU roles and explicitly says it is not proof of today's scope. The audited execution plan requires re-resolving the current champion, current stack/registry and recipes, then exact source-to-image bindings before quality collection. The current checkout contains `resolve_scope.py`, but it only cross-checks submitted scope and priors; it does not provide model-content hashes, build commits, recipes, or live image identity.

No current independently reviewed CPU-quality plan or current CPU paired capture was found in the checked-in `artifacts/` or `data/` trees. The available historical M4 quality plans are GPU-specific (`m4-gpu-quality-r8` and `m4-gpu-quality-rss-repair`, dated 2026-10-28); they cannot establish current CPU roles or CPU quality. The old CPU load successor at `/mnt/raid0/llm/tmp/inf22-m4-cpu-load-successor-20261029/` contains load/ownership fixtures and a stale `scope-cpu.json`, not a CPU quality plan or per-question quality captures. Its lease-safety evidence does not qualify the quality runner's owner-loss behavior.

Missing before this can become qualified:

1. Current champion/candidate source and build identity, with a content-verified executable and image-local libraries for both arms.
2. Independently derived current CPU role list and, per role, model SHA-256, build commit, and reviewed exact serving/quality recipe. Alias roles must resolve to their physical server without silently assuming shared model/image state.
3. A sealed plan with full mandated question/suite scope, prompt and expected-answer digests, runner digest, deterministic request settings, and independent plan digest captured at producer write time.
4. CPU quality runner entry and its owner-loss guardian/lease proof under the same source and packet intended for any future run.
5. Original baseline and candidate per-question outputs, errors and truncation, plus native summaries for every role/suite.

## Scope boundary

This is preparation only: no model inference, no production-kernel operation, no handoff/index edit, and no quality or promotion claim. Existing synthetic audit controls establish verifier behavior only; they do not fill any missing source binding or run evidence.

The relocated test resolves the adjacent auditor. Independent replay of the packet tests: `python3 -m pytest -q test_m4_quality_audit.py`, 12 passed; this is a synthetic consistency check, not an owner-loss or quality-run qualification.
