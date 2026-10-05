# NI05-26 — offline CPU command overrides

The canonical `NI-OFFLINE-CPU-CLI` task requires two leaf commands to accept explicit
CPU binary/configuration paths before resolving their production-store defaults, with
fresh-process checks that absent defaults still fail strictly. The reviewed source is
implemented and its focused fixtures passed off-host. The owning session published
the accepted source to app main `4244e72b2aa8aae9a92f684fcd5090a852223888`; all four
affected source/test files are byte-identical to the immutable tested candidate.

`scripts/benchmark/md_self_draft_ab.py` parses `--binary` before requesting the CPU
server default. `scripts/corpus/build_static_ngram_cache.py` uses a dataclass default
factory and resolves the CLI default only when an explicit directory is absent.
Neither change modifies the shared kernel-store provider. Original source commits are
`33b747875ae40888f7d783c6e7527c33590c6ebb` and
`b010c41ce7357dda19463369db1e7391be680dc5`.

Recovery run `37299780302` tested app candidate
`def18591f813070a20906f9d228ddd9dd0da9fd3` using workflow
`bd23af133bc305ed8224bc579b226eba0a31b09f`. Original `cpu-leaves.xml` contains
13 passed cases, zero failures, zero errors and zero skips. This includes six fresh
subprocess cases: explicit binary, help and absent default for the benchmark command;
explicit configuration, an actual `builder.main` call with a captured configuration,
and absent defaults for the corpus command. The fake executor only returns a fixture
result; no binary, model, serving process or inference runs. The existing large-scan
guard now declares its own unused temporary tool directory, allowing its intended
`allow-large-scan` refusal to execute without a production-store lookup. That one-line
fixture repair is `def18591f813070a20906f9d228ddd9dd0da9fd3`.

The original execution prefix was uploaded immediately and downloaded unchanged to
`/mnt/raid0/llm/worktrees/codex-ni05-validation-root-recovery-20261005/ni05-recovery-artifacts/cpu-leaves/`.
Its original XML SHA-256 is
`f754c34cdf3fc9c5033098b019e2611b5f87f65421d43ceec7610be9f18a333b`.
The same bundle retains `native-cpu-leaves/receipt.json`, the original request, log,
JUnit/readset bytes, phase context and exclusive unit readpath list. The producer's
bounded proposition records `fixture_execution_conformant=true` and command exit
zero. The owning session independently reopened both retained prefixes with the
existing reader, verifying all 923 readset hashes and original request/log/JUnit
seals, and independently confirmed the XML counts. The final off-host five-phase
verifier projection remains pending while the other phases run; this note does not
invent a tuple or reseal a record.

Ordinary guards ran in a separate, unpatched process and retained 2 passed cases:
the actual-host capacity guard and strict missing-GPU-store import. The synthetic RAM
bootstrap is a separate broad-unit context and is not evidence of production capacity.
No shared provider, production store, GPU source or measurement grader changed.

The ninth attempt `37295291738` timed out before artifact upload. Its retained log is
ordinary validation only; no original receipt or JUnit survived, and no historical
record was reconstructed. Broad-unit completion and API capture acceptance remain
separate task boundaries.
