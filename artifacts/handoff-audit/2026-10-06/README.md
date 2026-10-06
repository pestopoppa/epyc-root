# JEV-aware handoff audit evidence — 2026-10-06

`manifest.json` binds the 528-file original ROOT snapshot and its 3,558 unchecked task keys. S01–S15 inventories and reviews record disjoint coverage. MAIN decision files contain acceptance/rejection and exact applied append text. Historical overlap is separate from source-backed proposal review. This is documentation/source verification, not benchmark measurement or a ClaimTuple producer.

Original ROOT commit: `818841b22fb95a0f79a25e67f37583e3b94c5b7f`. Current handoff edits are a later state; original and accepted hashes must not be conflated. Historical boxes do not reopen completed tasks. No source implementation checkbox is completed by adding an audit refinement.

Run `python3 artifacts/handoff-audit/2026-10-06/validate_reviews.py --repo <ROOT-checkout> --coverage-only` for file/key/source accounting. Full mode also requires MAIN acceptance records and accepted text presence. Use `--applied-ref <published-audit-commit>` to verify the historical applied state after other sessions append to a handoff. Successful structural checks do not prove review quality or empirical acceptance.

Final MAIN report: [full audit and ranked preparation shortlist](../../../handoffs/completed/jev-aware-handoff-audit-2026-10-06.md). Twelve shard proposals accepted, one withdrawn duplicate rejected; historical adapter narrowing adds a thirteenth applied refinement. Original checkbox states are preserved. `validation.json` and `original-checkbox-preservation.json` record final checks.

Public task keys use `h:xxxx:xxxx:xxxx:xxxx`, a reversible grouped presentation of the original 16-hex SHA prefix. Concatenate the groups to recover the original key. Only typed key/reference fields are transformed; task text, source hashes and decoded document data are preserved. `serialization-provenance.json` records exact decoded equality with the immutable raw publication input and unchanged input bytes. This resolves numeric-looking hash false positives without changing or bypassing the privacy hook.
