# VERDICT q38fn-armP-ppl: **GO** (against PREDECLARED.md; PPL half only)
- PPL P (gate/up->IQ4_XS, rest = UD): 2.979 +/- 0.06187; UD re-run same job/quarter: 2.9868 +/- 0.06308; step1 UD 2.9925 / uniform 3.5244
- delta P vs UD re-run: -0.007800000000000029 (-0.2611490558457219 %); uniform-gap recovered vs step1 numbers: 1.0253807106598987
- PPL bar P <= 3.10: PASS; coherence bar: PASS (UD control ok)
- caveat: wikitext c512x40 chunks, SE ~0.06, so a delta < ~0.1 is inside the standard error (paired chunk-wise, but not KLD).
- Speed half (llama-bench) is a SEPARATE job; PASS bar there: pp256 >= +27%, pp5 >= +19% vs UD. Output out/q38fn-armP.gguf left in place for it.
