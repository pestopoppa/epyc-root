# Governing predeclared rule snapshot

Authority: `docs/design/gpu-zos-2-one-step-lag-design-20261024.md` §9.4.

- Source Git blob (lane HEAD at snapshot): `06fbdbc81c5504e72e42b0480e26534d3528d31f`
- Source SHA-256: `45fe64b79a3324b64bcf71f7fd8b9a76e3fbe322c26664d2a7481694d38876b4`
- Snapshot includes the exact effect, noise-floor and alternation formulas and original extension clause.

### 9.4 Speed gate (release images only; DEBUG figures never gate)

- **Metric:**
  - Per request: `timings.predicted_per_second` (server-reported decode tok/s).
  - Pairing: by prompt, using only prompts whose `tokens` are identical between the two passes compared. Identical tokens mean identical acceptance and tokens per step, so the ratio is a step-time ratio.
  - Excluded prompts are counted. If more than 25% of prompts are excluded from any comparison, speed is INCONCLUSIVE.
  - g(·) is the geometric mean over the paired prompts.
- **Effect:** S = g( √(B1ᵢ·B2ᵢ) / √(A1ᵢ·A2ᵢ) ) - 1.
- **Noise floor:** NF = max( |g(A2ᵢ/A1ᵢ) - 1|, |g(B2ᵢ/B1ᵢ) - 1| ).
  - **Unit:** percent of per-request decode tok/s (paired, geometric mean over 24 or fewer prompts, np4 spec-ON, this shape).
  - Also reported: the p10/p90 of A2ᵢ/A1ᵢ, and the 1a INDICATIVE prior (per-wave step-time range 1.55%, DEBUG build).
- **Alternation check (A/B/A/B):** g(B1/A1) - 1, g(B1/A2) - 1 and g(B2/A2) - 1 all have the same sign as S.
- **Thresholds:**
  - Minimum effect worth shipping: E_min = 1.0%.
  - Upper plausibility bound: U = 3.71% + 2·NF, the measured host share plus noise. The B arm can only remove host time from post_decode, plus C3's overlap of the same.
- **Verdict:**
  - **SHIP:** all correctness gates pass, S ≥ max(E_min, 2·NF), the alternation check holds, and S ≤ U.
  - **SUSPECT:** S > U. The effect is larger than the measured share can explain, so do not ship until the DEBUG attribution (§9.6) explains it.
  - **NULL:** |S| < max(E_min, 2·NF), with NF ≤ 1.85%. Close GPU-ZOS-2 with the numbers.
  - **UNDERPOWERED:** NF > 1.85% (half the ceiling), so even a perfect implementation could not clear 2·NF. One extension is allowed: append A3 and B3 and recompute S and NF over all 6 passes with the same rule. If it is still underpowered, the result is INCONCLUSIVE.
  - **REGRESS:** S ≤ -2·NF. FAIL.
