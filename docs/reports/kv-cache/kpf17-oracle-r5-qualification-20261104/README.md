# KPF-17 oracle r5 qualification

The completion predicate requires same-attempt native log, config and witness
files with matching hashes. Thirty-five model-free tests and publisher smoke
passed. The full model run remains pending. Build and runtime artifacts use
hash-checked hardlinks; in-place mutation is shared, and full-wrapper stop
precedence and same-UID race safety remain unproven.
