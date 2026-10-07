# Corrected SR5-LEAN-DOC-PROJECTION assessment and native-output proposal

Preparation only; no new workflow run, branch publication, native invocation, project write, or grading was performed.

## Owning task and exact sources

The owner is ROOT commit `5ab853a7`'s `handoffs/active/speculative-decoding-mtp-refresh.md`, task **SR5-LEAN-DOC-PROJECTION** (line 189 in that committed snapshot), with companion `VB-INF50-LEAN-DOC-PROJECTION`. Its requested contract is to regenerate/check the lean retired-field prose through the existing compiler `--dry-run`, bind the exact published Research master and current APP lean/compiler/topology/selection plus role closure, retain raw full-YAML delta and immutable source/cache verification, refuse any operative delta, and keep the outcome ungraded. This is not the separate SW-5 editing-guidance task.

The task's exact public source pins are Research `c49729505b6b85bcc2ef68255168014b4ae6a84d` and APP `f0df7ca2f801481d2024ad86c3ed37d60155430e`. Fresh bounded `ls-remote` checks observed APP main at f0df. Research main was first observed at c497 and then advanced to `aefa9a8347ec65f297c24e44021aad895e40b636`, a descendant. The current Research tip's `orchestration/model_registry.yaml` blob remains exactly c497's `0a54cff58ebef80ccefe9616cc6c303dfeec8d7f`; all K-bound Research input paths remain byte/blob-identical. The exact approved task pin therefore still describes the same inputs used by current public main.

The original hosted capture is pinned to APP `87ecbf18bc3d3793271d0eaf183e19900ad9726a` and Research c497. It is a valid diagnostic for those recorded bytes, not a native write of public f0df's current product. I compared the complete K-tracked APP file set against public f0df: all 10/10 files match, including the generated lean registry, compiler, selection code, topology, and lock inputs. The sole Research K-bound file matches c497 and current public tip. APP f0df's generated lean baseline is consequently the same data as the captured APP87 baseline.

## Corrected result

Independent PyYAML parsing of the entire captured native `--dry-run` stdout finds exactly one full-document semantic difference against the APP generated baseline: `speculative_decoding_policy.retired_fields.ngram_candidate_spec_type`. The projected value equals the exact public c497 Research master value. Thus the public f0df lean product is stale at that retired-field prose scalar, and the requested source-to-lean projection corrects it. This is the opposite of the earlier v1 plan's conclusion, which incorrectly used the unrelated shared Research checkout at f1c6 as current source. The v1 plan and v2 assessment are preserved as superseded; the correction does not revise the original artifact or its semantic report.

The captured native dry-run stdout is the YAML document and intentionally carries no generated-file banner. The f0df compiler's supported native writer (`--force`, `--output`, `--cache-key`) can preserve the actual generated product text including banner without changing APP checkout state: output and cache key can be directed into a fresh hosted custody directory. The banner code labels the hosted Research checkout path as a noncanonical input and names its canonical master source; that provenance is honest and should remain untouched. Native writer source was inspected at the exact public f0df commit. `--force` is supported and removes only the explicitly supplied cache-key path before compiling.

## Proposed reviewed recipe descendant

Before any publication, a MAIN-reviewed private recipe descendant should update the APP checkout pin from 87ecbf to exact public f0df and keep Research pinned to the task's c497 commit. Keep the exact derived 23-role closure below; the APP registry/topology/compiler/selection/dependency input blobs at f0df are all the same as the bound baseline. Preserve the current required `--dry-run` invocation, its raw stdout/stderr/argv/exit/timeout, semantic report, and unchanged source/cache proof. Add a second invocation of the same reviewed f0df native compiler:

```text
python -m src.registry.registry_compiler \
  --master research/orchestration/model_registry.yaml \
  --topology app/orchestration/stack_topology.yaml \
  --roles architect_critic architect_general coder_escalation embedder embedder_1 embedder_2 embedder_3 embedder_4 embedder_5 embedder_bge_m3 embedder_granite_97m_r2 embedder_multilingual_e5_base frontdoor ingest_long_context toolrunner vision_escalation worker worker_explore worker_fast worker_general worker_math worker_summarize worker_vision \
  --output "$RUNNER_TEMP/inf50-custody/result/native-output/model_registry.yaml" \
  --cache-key "$RUNNER_TEMP/inf50-custody/result/native-output/.lean_cache_key" \
  --force
```

The recipe must first prove the `native-output/` directory and both named paths are absent, create only that custody directory, and record the before-state. Run from the exact APP f0df checkout with the existing pinned Python and environment. Capture the writer's complete raw stdout/stderr, argv, working directory, exit, timeout, generated file bytes/mode/SHA-256, generated cache-key bytes/mode/SHA-256, and after inventory. Preserve the dry-run's raw YAML separately. Independently safe-load the generated file and require its full semantic diff against the exact f0df baseline to be the same one retired-field path, with the value equal to the exact c497 master; also check the banner is compiler-generated and contains the current master-input path plus canonical source-of-truth label, actual topology path, compile timestamp, cache key, and exact sorted role list. Never edit generated bytes or banner.

Record source Git status, all bound source payloads, and the APP checkout's pre-existing `.lean_cache_key` as opaque before/after state. All source bytes/status and that pre-existing cache state must remain unchanged. The new generated cache key belongs only inside the fresh custody output and does not authorize applying the product to the APP checkout. Preserve all existing null grade/claim/JUnit/native-receipt fields and classify the hosted product as ungraded diagnostic evidence; no new grade is introduced.

Exact role set (23): `architect_critic`, `architect_general`, `coder_escalation`, `embedder`, `embedder_1`, `embedder_2`, `embedder_3`, `embedder_4`, `embedder_5`, `embedder_bge_m3`, `embedder_granite_97m_r2`, `embedder_multilingual_e5_base`, `frontdoor`, `ingest_long_context`, `toolrunner`, `vision_escalation`, `worker`, `worker_explore`, `worker_fast`, `worker_general`, `worker_math`, `worker_summarize`, `worker_vision`. This is the original MAIN-reviewed role closure derived from APP compiled LEAN baseline at 87ecbf using actual `stack_manifest._load_master_registry` alias semantics; all APP inputs in that closure are identical at public f0df.

This descendant proposal is not yet a recipe commit and is not authorization to publish/run. It needs MAIN review and a final K binding before a single hosted capture. Do not overwrite original hosted artifacts, semantic report, v1 plan, or v2 assessment.
