KPF-17.4d multi-ubatch prefix witness review

Reviewed scratch candidate: /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174d-prefix-parser-fix-20261104/layout_witness.py
Historical source reviewed read-only at /mnt/raid0/llm/worktrees/kpf174-custody-r5-source-20261104 (HEAD 6ec877068936588b6d63dbba5842bbd540b92031): tools/server/server-context.cpp and src/llama-kv-cache.cpp. Source worktree status was clean.

Conclusion: `min(target prefill row positions) == prefix` identifies that the complete server batch has a target prefill row beginning at the prefix. It is not sufficient by itself to bind a particular physical layout snapshot to that target row or prove the fork boundary. In server-context.cpp, `decode()` emits one ITEM4_BEGIN/ROW sequence for the whole batch_view before calling llama_decode (around lines 4486-4507). In llama-kv-cache.cpp, `prepare()` loops through `ubatches`, calls `find_slot()` for each ubatch, and then applies that ubatch before advancing (around lines 847-865). `find_slot()` emits each layout using its own counter and logs stream/token counts and cells, but no ITEM4 ID, row range, or owner mapping (around lines 978-1001). A server batch can therefore own multiple layout records, and the parser currently considers every such layout after the batch-level min-position test.

Added synthetic regression in test_prefix_binding.py. One server batch contains a target row at pos=2 and a non-target row; the two layout records stand for successive ubatches. Only layout 21 has the requested slot's physical prefix. The existing candidate returns batch 7/layout 21, demonstrating that it can select the non-target ubatch snapshot because no association is available in the trace.

Added separate conservative candidate: layout_witness_conservative.py. For any batch containing target task/slot prefill rows, it rejects `len(layouts) > 1` with `ambiguous multi-layout target batch` before testing the prefix boundary or inspecting per-layout prefix matches. Single-layout boundary behavior remains covered. Original candidate remains unchanged.

Model-free test command from the scratch directory:
`python3 -B -m unittest -v test_prefix_binding.py`
Result: exit 0; 5 tests passed, covering original boundary/later-snapshot controls, duplicate boundary refusal, the current-candidate false association, conservative multi-layout refusal, and conservative single-layout acceptance.

Retained packet outcome: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174d-witness-r5-ready/out/STATE.json` was not edited and still records its existing `INVALID` state/reason. I made one read-only call to the scratch candidate with task=10, slot=1, prefix=1984 against the retained B trace; it returned batch 6/layout 8. This does not alter or supersede the prior runner outcome, but it is a discrepancy requiring owner review before any future use of that trace. Per instruction, no further retained-trace execution/regrading was done.

Limits: no source, live packet, grant, gate, retained trace, or prior verdict was edited. No build, model, inference, GPU, benchmark, publication, or source-bound GitNexus impact was run. The lane repository/index was not available as a source-bound GitNexus index, so this review makes no impact-clearance claim. The conservative refusal avoids an ambiguous association but may reject valid multi-ubatch traces; supporting those requires a future writer/format change that explicitly associates each layout with its item4 batch and row subrange.

Owner interpretation: the retained-runner parser used the earlier prefix-coverage-only selector; the subsequent scratch candidate adds a target-prefill position filter. Its read-only selection therefore does not contradict the runner error and cannot supply the missing control or change the original INVALID outcome. The later multi-ubatch counterexample still prevents adopting that candidate as a general binding proof.
