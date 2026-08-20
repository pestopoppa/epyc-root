**Achieving High-Throughput Inference of Large Mixture-of-Experts Models on Consumer Hardware via Hot-Expert Caching**

Large sparse Mixture-of-Experts (MoE) language models such as DeepSeek-V4-Flash-0731 present a classic resource imbalance on single-GPU consumer systems. The full quantized checkpoint may occupy approximately 90 GB, far exceeding the 32 GB of VRAM available on an RTX 5090, while system memory of 96 GB DDR5 is sufficient to hold the weights. Conventional layer-wise offloading leaves the majority of expert tensors in host RAM; each forward pass therefore repeatedly transfers the small subset of experts selected by the router across the PCIe bus. The resulting decode rate is typically limited to the mid-20-token-per-second range and becomes impractical for interactive use at long context lengths.

A targeted runtime optimization—hot-expert caching—changes this trade-off. The technique, implemented in the experimental buun-llama.cpp fork maintained by spiritbuun, monitors routing decisions over a sliding window of recent tokens, identifies the most frequently activated ("hot") experts, and pins those tensors in the residual VRAM that remains after the dense layers and the key-value cache have been allocated. Cold experts continue to reside in system RAM and are evaluated on the CPU only when actually selected. Because routing distributions in MoE models are highly skewed, a modest number of cached experts capture the large majority of activations, converting a PCIe-bound workload into a hybrid GPU/CPU computation whose effective throughput rises substantially.

### Measured Results on DeepSeek-V4-Flash-0731

On a single RTX 5090 paired with 96 GB of DDR5 memory the same 90 GB quantized checkpoint that previously sustained roughly 25 tokens per second reaches peak rates of 50.6 tokens per second once hot-expert caching is enabled. The improvement holds across a usable 256 k-token context window, demonstrating that the cache does not collapse under realistic long-context pressure. The absolute performance remains competitive with far more expensive multi-GPU configurations for interactive agentic and coding workloads.

### Recommended Runtime Configuration

The following command-line flags, drawn from successful production runs, illustrate a practical starting point:

```
-ngl 99 \
-sm layer \
-fa on \
-c 262144 \
--no-mmap \
-np 1 \
-ub 4096 \
-b 4096 \
-ctk f16 \
-ctv f16 \
-ot 'exps=CPU' \
--moe-cache on \
-t 16 \
-tb 16 \
--jinja \
--temp 1.0 \
--top-p 0.95 \
--min-p 0.0 \
--host 0.0.0.0 \
--port 8080
```

Key decisions encoded by these flags are:

- Maximum GPU layer offload (`-ngl 99`) places every dense component that fits into VRAM on the accelerator.
- Explicit expert placement (`-ot 'exps=CPU'`) keeps the bulk of the sparse weights in host memory.
- Activation of the MoE cache (`--moe-cache on`) enables the dynamic residency policy.
- Flash-attention and full-precision KV caches (`-fa on`, `-ctk f16`, `-ctv f16`) preserve quality while the large context (`-c 262144`) is accommodated by the remaining memory budget.
- Conservative micro-batch and batch sizes together with multi-threaded CPU execution keep the hybrid pipeline balanced.

Subsequent revisions of the same fork have further improved prefill latency, indicating that the caching infrastructure continues to receive active optimization.

### Design Rationale and Generality

The efficacy of hot-expert caching rests on two empirical regularities of contemporary MoE architectures. First, the router's selection distribution is heavily skewed: a small fraction of experts accounts for the large majority of token-level activations. Second, the set of hot experts changes only slowly across consecutive tokens, allowing a modest VRAM budget to maintain a high hit rate with infrequent rebalancing. When these conditions hold, the cost of occasional cache misses is more than offset by the elimination of repeated host-to-device transfers for the dominant experts.

The same principle has been explored in several independent llama.cpp derivatives and research prototypes. The distinguishing contribution of the buun-llama.cpp implementation is its tight integration with the existing tensor-override and flash-attention pathways, enabling a drop-in acceleration path for models whose total footprint exceeds consumer VRAM yet whose active footprint remains manageable.

### Practical Implications

For practitioners operating within a single high-end consumer GPU and a generous system-memory budget, hot-expert caching converts previously marginal MoE deployments into responsive, long-context inference engines. DeepSeek-V4-Flash-0731 at 50+ tokens per second with a genuine 256 k context illustrates the attainable operating point. As larger sparse models continue to appear, runtime techniques that exploit the natural sparsity of expert routing—rather than requiring proportional increases in accelerator memory—will remain an essential component of the local-inference toolkit.

### References

1. Vieirowski (@joaosump). Report of 50.6 tok/s inference of DeepSeek-V4-Flash-0731 on a single RTX 5090 + 96 GB DDR5 using spiritbuun's llama.cpp fork, 14 August 2026.
2. spiritbuun. buun-llama.cpp experimental fork, including MoE hot-expert caching and related KV-cache innovations (GitHub).
3. DeepSeek-AI. DeepSeek-V4-Flash-0731 model release and associated GGUF quantizations (Hugging Face, July–August 2026).
4. Community discussions and related MoE expert-caching implementations in llama.cpp forks and pull requests (LocalLLaMA, ggml-org discussions, 2026).
