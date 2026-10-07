# UFH-11 WEB-1 decision package (source review only)

ROOT task identity: `handoffs/active/amd-ai-lab-website-publication.md`, Git blob `04899d5786fd2f4ef5ea0cf4a0b24783963f7a5e`, SHA-256 `19cfa533cfbb8ac39b33dc78f459b532940dbcb342da574dd9e554ab85ef4c54` at ROOT 928a740. The open task asks for a contact destination and confirmation that the reviewed page is ready for public GitHub Pages launch. WEB-2 is subsequent publication/deployment work; this package does not authorize it.

The site source is private `pestopoppa/epyc-web` at `46024169d8b5dbea1cb0e2da36bdf1745b8b984c` (2026-09-25). Its `README.md` describes the review preview as `/amd-ai-lab/` on the existing hub; ROOT snapshot is `dashboard/static/amd-ai-lab/` and `PUBLICATION.md` binds the snapshot to that source commit. Full local preview address can be formed as `http://<hub-host>:8100/amd-ai-lab/`; no public site URL is recorded. GitHub API reports the repository is private with no homepage, and the Pages endpoint currently returns 404, so public Pages URL/configuration is not yet present.

The source `index.html` has a services section describing implementation and benchmarking support, but no contact link. The footer links only to evidence JSON. Searches of the complete tracked site files found no `mailto:`, booking URL, contact page, or CNAME. No actual mailbox, booking account, or domain contact destination is evidenced in the site source; the handoff mentions GoDaddy for a future domain connection but gives no domain string or mailbox setup. Do not invent one.

Options for the operator:

1. **Dedicated email address (handoff recommendation).** Provide an existing or newly configured address on the chosen domain, then add a `mailto:` call to action. This is the smallest static change and keeps scheduling under the sender's control. It exposes the address to spam and requires mailbox/forwarding maintenance. An address must be supplied before implementation; the source contains none.
2. **Booking link.** Supply a URL for an existing booking service and add a scheduling call to action. This avoids publishing an email address and gives prospects a direct scheduling path, but exposes availability and uses a third-party service/account that needs ongoing configuration.
3. **Contact page or form URL.** Supply an existing contact-page URL, or approve a separately implemented page. Linking to an existing page is straightforward; a new form on this static site needs a selected submission backend and privacy/spam handling, so that work is larger than a link and requires more choices.

Recommendation: use a dedicated contact email if an appropriate mailbox/forwarder already exists, consistent with the task's recommendation. If none exists, choose between creating one and providing an existing booking/contact URL; no source evidence supports selecting the address or external provider on the operator's behalf.

Reviewable before/after acceptance examples:

- Current: service copy says “I help teams select models…” with no contact action. Email choice: the same section gains one link whose `mailto:` target exactly matches the operator-supplied address. Booking choice: it gains one link whose `href` exactly matches the supplied booking URL. Contact-page choice: it gains one link to the supplied URL; if a new form is requested, backend/privacy scope is a separate implementation decision.
- Public-readiness confirmation: operator confirms “ready” or identifies requested edits after reviewing the private preview at `/amd-ai-lab/`; the page's public-launch contact action is visibly present and points to the supplied destination. Choosing “not ready” leaves WEB-2 unopened until the named edits are reviewed.

This is a decision package, not a site edit or a publication action. WEB-2 still requires the available-plan check for Pages on the private repository, domain configuration, HTTPS/link/responsive checks, and a separate publication step. WEB-3 remains conditional on a future measurement window and explicitly does not authorize that run.

## Reviewable page excerpt and evidence boundary

The current page presents the headline “More AI. From your AMD hardware.” and says it helps teams select models, deploy optimized CPU and ROCm kernels, and tune speculative decoding, memory placement, and concurrency. It describes reproducible benchmarking and workload validation. The seven displayed model/service cards are Qwen3.8-27B; Qwen3.6-35B-A3B MI210; Qwen3-VL-30B-A3B; Qwen3.6-35B-A3B EPYC CPU; Qwen3.8-Flash-Next; Whisper large-v3-turbo; and Qwen3-TTS 0.6B.

The page's evidence claims need to be read with these current source limits: it lists the current frozen production kernels; KV-cell evidence is exploratory at n=1 per cell; absent np8 cells are guard skips or load OOMs, not zero measurements; wall-clock aggregate results differ from per-request decode and qualification curves; the CPU grid for Flash-Next is explicitly unmeasured because the September 24 sweep was skipped; and predecessor-build or predecessor-weight numbers do not establish current speed. These are measurement qualifications, not new conclusions about comparative performance.

Private source review links (all pinned to source commit `46024169d8b5dbea1cb0e2da36bdf1745b8b984c`): [index.html](https://github.com/pestopoppa/epyc-web/blob/46024169d8b5dbea1cb0e2da36bdf1745b8b984c/index.html), [app.js](https://github.com/pestopoppa/epyc-web/blob/46024169d8b5dbea1cb0e2da36bdf1745b8b984c/app.js), [data/catalog.json](https://github.com/pestopoppa/epyc-web/blob/46024169d8b5dbea1cb0e2da36bdf1745b8b984c/data/catalog.json), and [EDITORIAL.md](https://github.com/pestopoppa/epyc-web/blob/46024169d8b5dbea1cb0e2da36bdf1745b8b984c/EDITORIAL.md). Git blob IDs at that commit: `index.html` `a73e9737214e12ff3e6afe09058f76a66d266e04`; `app.js` `018c3499ad6eec1105a18724f688daf07b7bb850`; `data/catalog.json` `a8e2be2ff99cdb885832ea892382c9d4d1b278fe`; `EDITORIAL.md` `87adc3cfbf6ca286109c35515a037fb18bd12d03`.

Retained September 25 visual artifacts are available for review without requiring hub access: [retained desktop screenshot](desktop-20260925.png) (SHA-256 `b1ae30b40811beb1df35453c1feea7f68e7c2929c216e4fb29bdbf0a5cd48a43`, 575,663 bytes) and [retained mobile screenshot](mobile-20260925.png) (SHA-256 `9b926e7006df2b1f0ccb267d54bc982bcb2a615660ba77e5df405d6271bb78e2`, 498,592 bytes). These are retained screenshots from September 25, not a newly rendered current preview; use them for layout context, while source links above are the current content authority.

The review and contact-destination choices are separate: first review the page excerpt/source and retained screenshots; independently provide an email, booking, or existing contact-page destination if one is selected. No dashboard login is required to inspect the supplied material, and no destination is asserted as already configured.

Default: no contact destination is invented and no public launch occurs until the operator supplies the destination and confirms readiness. Source tasks and other independent backlog work continue.
