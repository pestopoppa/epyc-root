# Tulving SRS workflow comparison controls — 2026-10-08

Research main `72832ef6eed7d0439be7853a23d23efb876d48b3` now supplies the opt-in `--compare-srs-to` gate. It rejects unequal scorer versions, gold bindings, bin definitions or populated bin sets before JSON, Markdown or fixture capture. Reports show the populated bins and native counts. SRS/CAS arithmetic remains unchanged; matching bins alone do not establish equal book difficulty.

[Original CI run](https://github.com/pestopoppa/epyc-root/actions/runs/37763063057), attempt 1 at ROOT `5962987afc3775ee635bc334492c62ad82c6f37f`, passed all 32 controls (27 scorer cases and five comparison helper cases), with zero failures, errors or skips. MAIN independently verified the original JUnit case multiset, receipt seal, all 27 original carrier readsets and unchanged source snapshots. [MAIN native acceptance](MAIN-original-native32-acceptance.json) uses the existing carrier and shared Judged/Located grade. The original carrier has no generated-output field; no newer schema fields were reconstructed.

Original JUnit SHA-256: `ec37a3c44c26e19ba705769d599ddb0efb2328e192582c1d80c267214df1c87d`. Original artifact ZIP SHA-256: `4f456d529255307ca846650114ad37951c79c4595d397f83690cf9b080f6fd32`. Immutable originals remain in `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/m12g-original-ROOT596-event-heldwatcher-PREP-20261008/actual-operation`.

[MAIN publication acceptance](MAIN-original-Research-main-FF-acceptance.json) verifies 53 original command results and both normal leases, including release and token removal. Research main advanced once from `daa1855` to `72832ef6` by a normal fast-forward push.

This ROOT integration copies the exact six recipe blobs tested at `5962987`; its new integration commit does not redefine the original event source. These are model-free source controls, not model quality, protocol ratification, inference, production deployment or historical tuple backfill. M-12f and M-12i retain their separate work.
