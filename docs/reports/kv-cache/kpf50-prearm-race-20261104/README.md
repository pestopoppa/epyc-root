# KPF-50 pre-arm parent-loss control

One model-free, own-child subprocess test passed. It records a child observing
its launching parent, kills and reaps that exact parent before releasing the
child to call the candidate `parent_death_kill`, and verifies that the child
refuses with exit 125. A test-owned subreaper then reaps it and proves ECHILD.

This checks the pre-arm parent-change refusal in isolation. It does not prove
the native launcher calls this path, contain arbitrary descendants, cover the
smaller race after the parent check, establish same-UID safety, or qualify a
profiling run. No model or GPU ran.
