# CAFE-2 expert-union callback source proof (unexecuted proposal)

Pinned source: production v10 `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, read only. No active package, worktree, production source, publisher or grant was modified.

The named `ffn_moe_topk-<layer>` tensor is the actual selected routed expert IDs, not router probabilities or predicted independent union. `build_moe_ffn` names that selected tensor; qwen35moe executes its MoE FFN in every trunk layer. `llama_model_n_layer()` is the trunk count excluding MTP layers, and the proposal explicitly requires intended qwen35moe E=256,K=8,40-layer metadata before capture. The public callback is attached only to the target context and active only for its verify decode; MTP context callbacks are not configured.

`ggml_argsort_top_k` returns a VIEW over E-wide argsort rows. The view is a graph node because the graph builder only classifies OP_NONE as leaves. The split graph is a view of the original node range. Although the scheduler skips view ops during assignment/split selection, its callback evaluation loop has no view skip: it asks every split node, computes through the selected node, synchronizes the split backend, then calls observation with ask=false. The CPU backend graph optimizer is NULL, so this source path does not remove the topk view. The proposal reads each token's K I32 IDs with the actual nb[1] stride and a bounds check, preserving all IDs and union members. This is source-level proof of that pinned CPU path, not a native callback observation. If another backend optimizer removes the view or shape, coverage fails UNKNOWN; do not generalize callback availability without revalidation.

An instrumented callback changes graph evaluation boundaries/synchronization. Therefore `--expert-census` is a separate execution arm with no reported timings. The plain invocation installs no cb_eval and remains the timing arm. Both emit complete prompt/boundary/draft token plans; every window binds rep/cell ordinal, position, rows and target token IDs. Every layer record binds tensor name, layer, full shape/strides, E/K, all K IDs per token, union IDs/count. The terminal checks exactly one observation for each expected trunk layer; malformed types/shapes/strides, duplicate layers/IDs, invalid expert IDs, decode error, output failure or missing coverage remains UNKNOWN. Union sum counts (layer,expert) pairs, not a global ID union across layers. Shared experts are explicitly outside this routed-expert census; their separate per-token cost term remains separate.

The model default `load_mtp=false` skips MTP tensors even when metadata reports nextn layers; qwen35moe MTP graph asserts nextn.eh_proj exists. The proposal sets mp.load_mtp=true before loading, and supplies a separate unapplied one-line CAFE-4 model-load patch. It does not retrofit old binaries or old timing records with this fix.

## Exact pinned source excerpts

### src/llama-graph.cpp:2056

```text
2056:     // select experts
2057:     ggml_tensor * selected_experts = selected_experts_in;
2058:     if (selected_experts == nullptr) {
2059:         selected_experts = ggml_argsort_top_k(ctx0, fuse_moe_weights ? logits : selection_probs, n_expert_used); // [n_expert_used, n_tokens]
2060:         cb(selected_experts->src[0], "ffn_moe_argsort", il);
2061:     }
2062:     cb(selected_experts, "ffn_moe_topk", il);
2063: 
```

### src/llama-context.cpp:2785

```text
2785: llm_graph_cb llama_context::graph_get_cb() const {
2786:     return [&](const llama_ubatch & ubatch, ggml_tensor * cur, const char * name, int il) {
2787:         if (il >= 0) {
2788:             ggml_format_name(cur, "%s-%d", name, il);
2789:         } else {
2790:             ggml_set_name(cur, name);
2791:         }
```

### ggml/src/ggml.c:5443

```text
5443: struct ggml_tensor * ggml_argsort_top_k(
5444:         struct ggml_context * ctx,
5445:         struct ggml_tensor  * a,
5446:         int                   k) {
5447:     GGML_ASSERT(a->ne[0] >= k);
5448: 
5449:     struct ggml_tensor * result = ggml_argsort(ctx, a, GGML_SORT_ORDER_DESC);
5450: 
5451:     result = ggml_view_4d(ctx, result,
5452:                 k, result->ne[1], result->ne[2], result->ne[3],
5453:                    result->nb[1], result->nb[2], result->nb[3],
5454:                 0);
5455: 
5456:     return result;
```

### ggml/src/ggml.c:7252

```text
7252:     if (node->op == GGML_OP_NONE && !(node->flags & GGML_TENSOR_FLAG_PARAM)) {
7253:         // reached a leaf node, not part of the gradient graph (e.g. a constant)
7254:         GGML_ASSERT(cgraph->n_leafs < cgraph->size);
7255: 
7256:         if (strlen(node->name) == 0) {
7257:             ggml_format_name(node, "leaf_%d", cgraph->n_leafs);
7258:         }
7259: 
7260:         cgraph->leafs[cgraph->n_leafs] = node;
7261:         cgraph->n_leafs++;
7262:     } else {
7263:         GGML_ASSERT(cgraph->n_nodes < cgraph->size);
7264: 
7265:         if (strlen(node->name) == 0) {
7266:             ggml_format_name(node, "node_%d", cgraph->n_nodes);
7267:         }
7268: 
7269:         cgraph->nodes[cgraph->n_nodes] = node;
7270:         cgraph->n_nodes++;
```

### ggml/src/ggml.c:7494

```text
7494: struct ggml_cgraph ggml_graph_view(struct ggml_cgraph * cgraph0, int i0, int i1) {
7495:     struct ggml_cgraph cgraph = {
7496:         /*.size             =*/ 0,
7497:         /*.n_nodes          =*/ i1 - i0,
7498:         /*.n_leafs          =*/ 0,
7499:         /*.nodes            =*/ cgraph0->nodes + i0,
7500:         /*.grads            =*/ NULL, // gradients would need visited_hash_set
7501:         /*.grad_accs        =*/ NULL,
7502:         /*.leafs            =*/ NULL,
7503:         /*.use_counts       =*/ cgraph0->use_counts,
7504:         /*.visited_hash_set =*/ cgraph0->visited_hash_set,
7505:         /*.order            =*/ cgraph0->order,
7506:         /*.uid              =*/ 0
7507:     };
```

### ggml/src/ggml-backend.cpp:1419

```text
1419: 
1420:     for (int i = 0; i < sched->n_splits; i++) {
1421:         struct ggml_backend_sched_split * split = &sched->splits[i];
1422:         split->graph = ggml_graph_view(graph, split->i_start, split->i_end);
1423: 
1424:         // Optimize this split of the graph. This needs to happen before we make graph_copy,
1425:         // so they are in sync.
1426:         ggml_backend_graph_optimize(sched->backends[split->backend_id], &split->graph);
1427: 
1428:         // add inputs to the graph copy so that they are allocated by ggml-alloc at the start of the split
```

### ggml/src/ggml-backend.cpp:1691

```text
1691:         } else {
1692:             // similar to ggml_backend_compare_graph_backend
1693:             for (int j0 = 0; j0 < split->graph.n_nodes; j0++) {
1694:                 struct ggml_tensor * t = split->graph.nodes[j0];
1695: 
1696:                 // check if the user needs data from this node
1697:                 bool need = sched->callback_eval(t, true, sched->callback_eval_user_data);
1698: 
1699:                 int j1 = j0;
1700: 
1701:                 // determine the range [j0, j1] of nodes that can be computed together
1702:                 while (!need && j1 < split->graph.n_nodes - 1) {
1703:                     t = split->graph.nodes[++j1];
1704:                     need = sched->callback_eval(t, true, sched->callback_eval_user_data);
1705:                 }
1706: 
1707:                 struct ggml_cgraph gv = ggml_graph_view(&split->graph, j0, j1 + 1);
1708: 
1709:                 enum ggml_status ec = ggml_backend_graph_compute_async(split_backend, &gv);
1710:                 if (ec != GGML_STATUS_SUCCESS) {
1711:                     return ec;
1712:                 }
1713: 
1714:                 // TODO: pass backend to the callback, then the user can decide if they want to synchronize
1715:                 ggml_backend_synchronize(split_backend);
1716: 
1717:                 if (need && !sched->callback_eval(t, false, sched->callback_eval_user_data)) {
1718:                     break;
1719:                 }
1720: 
1721:                 j0 = j1;
```

### ggml/src/ggml-cpu/ggml-cpu.cpp:202

```text
202:     /* .graph_plan_create       = */ ggml_backend_cpu_graph_plan_create,
203:     /* .graph_plan_free         = */ ggml_backend_cpu_graph_plan_free,
204:     /* .graph_plan_update       = */ NULL,
205:     /* .graph_plan_compute      = */ ggml_backend_cpu_graph_plan_compute,
206:     /* .graph_compute           = */ ggml_backend_cpu_graph_compute,
207:     /* .event_record            = */ NULL,
208:     /* .event_wait              = */ NULL,
209:     /* .graph_optimize          = */ NULL,
210: };
```

### src/models/qwen35moe.cpp:177

```text
177:     // MTP/NextN layers are loaded as extra decoder blocks but not executed in the main pass.
178:     for (int il = 0; il < n_layer; ++il) {
179:         res->t_layer_inp[il] = inpL;
180: 
```

### src/models/qwen35moe.cpp:494

```text
494: ggml_tensor * llama_model_qwen35moe::graph::build_layer_ffn(ggml_tensor * cur, const int il) {
495:     // Check if this is an MoE layer
496:     GGML_ASSERT(model.layers[il].ffn_gate_inp != nullptr);
497: 
498:     ggml_tensor * moe_out =
499:         build_moe_ffn(cur,
500:             model.layers[il].ffn_gate_inp,
501:             model.layers[il].ffn_up_exps,
502:             model.layers[il].ffn_gate_exps,
503:             model.layers[il].ffn_down_exps,
504:             nullptr,
505:             n_expert, n_expert_used,
506:             LLM_FFN_SILU, true,
507:             hparams.expert_weights_scale,
508:             LLAMA_EXPERT_GATING_FUNC_TYPE_SOFTMAX, il,
509:             nullptr, model.layers[il].ffn_gate_up_exps,
510:             model.layers[il].ffn_up_exps_s,
511:             model.layers[il].ffn_gate_exps_s,
512:             model.layers[il].ffn_down_exps_s);
513:     cb(moe_out, "ffn_moe_out", il);
```

### src/llama-model.cpp:2473

```text
2473:         /*.use_mmap                    =*/ true,
2474:         /*.use_direct_io               =*/ false,
2475:         /*.use_mlock                   =*/ false,
2476:         /*.check_tensors               =*/ false,
2477:         /*.use_extra_bufts             =*/ true,
2478:         /*.no_host                     =*/ false,
2479:         /*.no_alloc                    =*/ false,
2480:         /*.load_mtp                    =*/ false,
2481:     };
2482: 
```

### src/models/qwen35moe.cpp:39

```text
39:     const bool mtp_only = (hparams.n_layer_nextn > 0) && (ml.get_weight("blk.0.attn_norm.weight") == nullptr);
40:     const int trunk_flags = mtp_only ? TENSOR_NOT_REQUIRED : 0;
41:     int mtp_flags = !ml.load_mtp ? TENSOR_SKIP : 0;
42: 
```

### src/models/qwen35moe.cpp:559

```text
559:     const int il = hparams.n_layer();
560:     const auto & layer = model.layers[il];
561: 
562:     GGML_ASSERT(layer.nextn.eh_proj    && "MTP block missing nextn.eh_proj");
563:     GGML_ASSERT(layer.nextn.enorm      && "MTP block missing nextn.enorm");
564:     GGML_ASSERT(layer.nextn.hnorm      && "MTP block missing nextn.hnorm");
565:     GGML_ASSERT(layer.ffn_gate_inp     && "MTP block missing ffn_gate_inp");
```
