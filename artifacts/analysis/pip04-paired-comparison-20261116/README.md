# PIP-04 PARSER-PAIRED-COMPARISON (2026-11-16, zero inference)

Question: are the parser arms' overall differences on the 200-PDF corpus distinguishable from per-document noise?
Method: paired percentile bootstrap over documents, B=10000, seed 20261116; diff = a minus b; higher = better (overall = mean of NID/TEDS/MHS; TEDS paired on the 42 table docs, MHS on 106 heading docs where both arms have the score). Failed docs are censored, never zero. Script and full output (all pairs, all four metrics, two docsets): `paired_bootstrap.py`, `paired_bootstrap.json`; run copy under `/mnt/raid0/llm/tmp/pip04-paired-comparison-20261116/`.
Inputs: docling + LightOnOCR + ODL hybrid r2 `evaluation-final.json` (`/mnt/raid0/llm/tmp/parser-*-200pdf-*/out/`), ODL-013 r2 raw `evaluation.json` for liteparse/opendataloader(local)/pdftotext (`/mnt/raid0/llm/archives/pip04-odl013-r2-20261107/run/prediction/`; the committed copy is pseudonymized). Marker excluded (score withheld by the handoff). legacy_router is identical to pdftotext.
Docsets: 199 docs common to all arms (ODL hybrid censored doc 0141); 200 docs for the arms other than ODL hybrid. Conclusions are the same in both.

## Overall, paired (199 common docs)
| a - b | diff | CI95 |
|---|---|---|
| docling - LightOnOCR | -0.0028 | [-0.018, +0.013] |
| docling - LiteParse | +0.0128 | [-0.004, +0.031] |
| LightOnOCR - LiteParse | +0.0156 | [-0.006, +0.037] |
| ODL hybrid - docling | +0.0083 | [-0.005, +0.021] |
| ODL hybrid - LightOnOCR | +0.0055 | [-0.011, +0.024] |
| ODL hybrid - LiteParse | +0.0211 | [+0.004, +0.039] (excludes 0) |
| docling / LightOnOCR / ODL hybrid / LiteParse - ODL local | +0.049 / +0.052 / +0.058 / +0.037 | all exclude 0 |
| every arm - pdftotext | +0.27 to +0.33 | all exclude 0 |

## Secondary metrics
- NID: docling is worse than LightOnOCR (-0.027, [-0.037, -0.018]) and ODL hybrid (-0.024, [-0.035, -0.015]); LightOnOCR beats LiteParse (+0.016, [+0.003, +0.029]).
- TEDS (n=42): docling beats LiteParse (+0.144, [+0.079, +0.216]) and ODL hybrid (+0.051, [+0.017, +0.097]); docling vs LightOnOCR +0.054, CI [-0.008, +0.132] (not distinguishable).
- MHS (n=106): no pair among docling/LightOnOCR/ODL hybrid/LiteParse excludes 0.

## Finding
Docling, LightOnOCR, ODL hybrid and LiteParse are statistically tied on overall score (all CIs between them include 0, except ODL hybrid over LiteParse, +0.021 [+0.004, +0.039]); the point-estimate order docling 0.891 < LightOnOCR 0.896 < ODL hybrid 0.9035 is not resolved by 200 documents. All four clearly beat ODL local (about +0.04 to +0.06) and pdftotext/legacy_router (about +0.3). The component picture is real though: LightOnOCR and ODL hybrid win reading order (NID) over docling, docling wins tables (TEDS) over LiteParse and ODL hybrid; no arm wins headings. Nothing here supports a routing or adoption decision on overall score alone; ODL hybrid is the cheapest strong arm (0.56 s/doc vs LightOnOCR 19.9 s/doc), a latency fact not a paired-score fact. Caveats: ODL hybrid covers 199 docs (doc 0141 censored, anomalous in every arm); sample is one 200-PDF corpus; CIs are per-metric, not multiplicity-adjusted. Observation only; marker still excluded.
