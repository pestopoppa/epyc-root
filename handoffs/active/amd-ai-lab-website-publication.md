# AMD AI Lab website publication

**Status:** active — private source and dashboard preview published; public launch awaits the operator's review and contact destination.
**Owner index:** [user-facing-harness-index.md](user-facing-harness-index.md) (UFH-11).

## Start here

- Source: private `epyc-web` at `/workspace/repos/epyc-web`, `main` `4602416`.
- Review preview: dashboard hub `/amd-ai-lab/`, root snapshot `dashboard/static/amd-ai-lab/`, source commit recorded in `PUBLICATION.md`.
- Source-of-truth for measurement selection: `epyc-web/EDITORIAL.md`; page data: `epyc-web/data/catalog.json`.
- Production kernel is frozen `ffc1bac82` (`production-consolidated-v10`). Do not change it for site work.

## Completed scope

- [x] Publish the private `epyc-web` source repo and registered dashboard preview. ✅ 2026-09-25 — latest site source `4602416`, root snapshot merged to `main` `a07408f2`.
- [x] Build a compact dark AMD catalog with model workspaces, source links, and configuration details. ✅ 2026-09-25 — seven cards, hardware grouping, search and filters.
- [x] Show explicit weight quantization and measured performance matrices on every card. ✅ 2026-09-25 — unmeasured cells remain labeled; speech uses thread × workload rather than LLM context.
- [x] Audit best current results and add Qwen3.8-Flash-Next. ✅ 2026-09-25 — frozen-v10 quality: MMLU-Pro 151/200 and GPQA 127/195 on UD-IQ4_XS; older 52.661 tok/s predecessor run identified separately.
- [x] Validate the site and dashboard publication. ✅ 2026-09-25 — Chromium desktop/mobile suite passes all seven workspaces; live dashboard checks confirmed Flash-Next and source evidence.

## Next actions

- [ ] **WEB-1 — operator publication choice:** provide the contact destination (email, booking link, or contact page) and confirm the reviewed page is ready for public GitHub Pages launch. Recommendation: use a dedicated contact email unless a booking flow already exists. This choice is needed to make the services section actionable and to fix the public launch point.
- [ ] **WEB-2 — publish the reviewed snapshot:** configure GitHub Pages for the private `epyc-web` repo under the available plan, verify its public URL, connect the GoDaddy domain, then check HTTPS, links, responsive layout, and that no private research paths or credentials are exposed.
- [ ] **WEB-3 — refresh evidence when measured:** if a frozen-kernel Flash-Next UD-IQ4_XS CPU np × context throughput sweep is produced, replace the card's unmeasured grid with its source-backed cells. The September 24 sweep was explicitly skipped by the operator; this task does not authorize running it.

## Measurement limits

The Qwen3.6 GPU 112.676 and 310.958 tok/s maxima were measured on predecessor `ef81196d5`, not frozen v10. Its current card uses the best located frozen-v10 cells, 104.8 tok/s per request and 229.6 tok/s wall aggregate at different operating points. Flash-Next's 52.661 tok/s post-BIOS study likewise used `ef81196d5` and IQ4_XS-uniform weights; the served model uses UD-IQ4_XS. Do not present either predecessor result as frozen-v10 throughput.
