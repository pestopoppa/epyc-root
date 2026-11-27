# Native sampler replay of the four-token tie

The original fixture supplies four equal probabilities and seed 3. On frozen v10's native CPU sampler, greedy selected token 0 in the original order. With identical logits, top-p at 0.5 retained IDs 1 and 3 and the seeded draw selected 1. Its log probability was −1.386294 over all four candidates and −0.693147 over the retained pair. Applying top-k=2 before top-p=0.5 left only token 0. These changes occur after logit formation, so they provide a control for the activation-packing replay. [Original receipt](../spec-filter-ties-20261126/SPEC-FILTER-TIES.json) · [Native records](SPEC-FILTER-TIES.json)

The 48 records span four inputs (equal logits, a one-ULP gap, a wide gap and a tie with two masked logits), two input orders and six filter sequences. The whole-tie reference keeps every token at a tied cutoff. Native retained support differed from that reference in 14 records. Unfiltered native greedy always selected the first maximum in input order. For each seeded draw the harness starts a fresh native sampler at offset zero and verifies repeatability. Native retained probabilities agree with the stored log probabilities to within 1e−6. Full and retained masses sum exp(logit) on the corresponding support. The original Python PIT uniformity test passes separately. Its RNG stream is independent of the native RNG stream.

Run from the repository root on the EPYC host using a CPU grant. The replay verifies the loaded library paths and hashes against the store manifest. Its stdout reproduces the JSON byte for byte.

```sh
export LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin
python3 data/spec-filter-ties-20261127/replay.py | cmp - data/spec-filter-ties-20261127/SPEC-FILTER-TIES.json
```
