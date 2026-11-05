# Prospective KPF-17.4 oracle input guard

This standalone structural guard is **not wired into a launcher or judge**. A future caller must bind its nonempty expected cell IDs and geometry to a predeclared plan, call `validate_launch`, and refuse to judge if it returns any errors. It does not verify that IDs encode their declared geometry, prove control independence, run inference, or judge model outputs. Historical verdicts and exposed cells remain unchanged.

The need is visible in research commit `1157adc2f007d1b0c45ddc6daf91eafc45358df7`, `scripts/benchmark/kpf174/kpf174_swa_drafter.py` (SHA-256 `d008fc6bd0e2541b92f1cc7ef1acb72931332d59743c3d11615a3cf8c3d85725`). Lines 126 and 133 declare source slot 0 and both arms; lines 251–265 iterate however many arms are present and explicitly accept `fork_src_slot` of `None`. The delegated `kpf13_restore_ab.py` `judge_run` checks fork token count but not source slot. Line 281 uses `zip(judged, scope)`, which truncates unequal lists; the normal `analyze` caller constructs them together, so this is a potential API misuse, not evidence that any historical run was affected. No historical result was rejudged.

The guard checks the planned cell set, controls, arm cardinality and source, and the partial-noop mutation's pruning scope. It must be used before, not as a replacement for, the declared output judge. Run its model-free controls with:

```sh
python3 -m unittest discover -s docs/reports/kv-cache/kpf174-oracle-preflight-20261105 -v
```
