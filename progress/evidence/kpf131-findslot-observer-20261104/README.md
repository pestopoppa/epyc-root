# KPF-13.1 allocator entry observer

Row `kvu-kpf131-findslot-observer-20261104` passed the publisher's four-CPU smoke and was published on 2026-11-05. The full attempt is pending. The runner observes two `find_slot` entries in each of the honest and skip-apply model-free fixture cases, checks their sequence IDs, and records the pinned executable and five mapped historical-image llama/ggml DSOs at the breakpoints. The fixture itself detects the mutation; the observer does not claim to detect the placement mutation.

The smoke is a preparation check, not the full-attempt result. This observer does not establish a physical layout, request/task binding, continuous custody, or a historical control. The scratch packet is `/mnt/raid0/llm/tmp/kvu/observer-findslot-v1`; the committed scripts and declaration describe its contents. The earlier fixture attempt was INVALID under its full custody rule; its R2 qualification remains pending.
