---
schema: epyc.brief.v1
id: NARIQ-KLD-MASK-1
box_text_sha: a3b169c61cfd755e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
approach: 'Work on experimental/ear-kld-column-20261022 (fresh from production; v10 frozen). Add an optional --kld-mask file
  of per-token 0/1 flags to llama-perplexity --kl-divergence; masked KLD printed in a new block after the existing lines so
  old stdout stays byte-identical; factor the masked accumulation into a pure header (like kld-ear.h) so it is unit-testable
  by a file-scoped g++ compile.

  '
acceptance: cd /mnt/raid0/llm/llama.cpp-experimental && g++ -std=c++17 -Itools/perplexity tests/test-kld-mask.cpp -o /tmp/test-kld-mask
  && /tmp/test-kld-mask
new_tests:
- epyc-llama:tests/test-kld-mask.cpp
non_goals:
- never touch production-consolidated-v10 or its tree
- no model run
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
---
