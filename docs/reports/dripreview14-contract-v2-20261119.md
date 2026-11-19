# Progressive FINAL contract-v2

D-RI-PREVIEW-1.4 implementation: `scripts/benchmark/repl_contract_variant.py` loads
producer Git objects at epyc-orchestrator `fe2c0b9e3b5c127aef300229a66a9e5197a8a93a` and repairs only
INTRO and early-FINAL episode control. Turn 1 discloses the seven keys and Q7 wait
rule. Rejected submissions add feedback to retained turn observations; later calls
continue normally. The oracle still scores wrong dicts wrong and non-dicts bad_final
at/after Q7. Corpus, retrieval, questions and renderings remain pinned producer code.

Eight zero-model tests pass (`python3 tests/benchmark/test_repl_contract_variant.py`):
turn-1 schema/wait, recovery through Q7 in every rendering, persistent variables and
feedback, wrong submissions on turns 7/8/9, non-dict bad_final, exhausted turn cap,
pinned helper loading, rejection of unbound cells, and unchanged corpus/renderings/oracle.
This is implementation evidence, with no served-model improvement claim.

Variant `progressive-final-contract-v2` binds source hashes, patched fixture hash and wrapper hash
in every retained cell and final result. Variant SHA-256:
`00300557d0016d12c803128b1df05bf701da713cc21a9737a68c302a9fcb0b96`.
Wrapper SHA-256: `b5681dd5f09d6f2f7f6937f96a0b6f6a61b63b2791e86e3b79707d23c20e25bf`.
A resume directory must carry the identical binding. The row retains its own small
lane-owned wrapper input so lane reaping cannot remove the executable repair. No
producer source tree, log or binary is copied into the lane or evidence directories.

Prospective row: `dripreview14-contract-v2-20261119`; port 9466, 24 CPU threads under grant, same worker
Qwen3.6-35B-A3B-MTP-Q8_0, production CPU binary SHA-256
`4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c`.
Predeclaration frozen before smoke: `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-20261119/PREDECLARED.md`, SHA-256
`c2647240a8d0f63a9e953b9705c14722444638bcad3c91c2bc95947bfcab0f38`.
Input manifest: `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-20261119/SOURCE.sha256`, SHA-256
`f12976a9d2393ea6f8d6b67c2abaec297f4a2d81f8594c428d219a4cc879f7c4`.
Native result: `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-out-20261119/result.json`;
fresh sibling `cells/`, separate row `out-smoke/RESULT.json`. No old cells imported.

Question: does the corrected contract permit a rendering separation? Planning gap
>=0.30, n=30 paired, exact McNemar p<0.05/3 at full n; same prior uncertainty and
~65% planned power, no interim success claims. Futility-only looks: n=10 all cells
>=9 correct or all zero; n=20 max-min<=2 correct. Void if bad_final exceeds 20% of
planned n. Stop on deadline/STOP, binary/linkage/pin mismatch; no extension following
futility. Booking 15000 s covers the enforced >=7 calls plus added contract tokens;
this is a planning ceiling, not a timing measurement.

The original result remains frozen futility. This diagnostic does not implement the
separate D-RI-PREVIEW-1.2 full-question-up-front redesign. Existing prospective
VB-REPL-COMPOSITE-WRITE wiring covers this native schema with its additional binding;
no new measurement source or grading ladder is introduced.

Publication initially refused the old box as non-inference with no model identity.
The owned box now explicitly names the model, inference class and existing stop
rules; no gate was changed. GitNexus status/impact found no index; its prescribed
index wrapper was refused by CPU admission, so no graph risk rating is claimed.

Publication: `publish_row.py --smoke-now` reported **SMOKE PASS** on CPUs
140-143 at 2026-11-19T10:33:31Z (smoke predicate, clean partial-native rc=75),
then PUBLISHED the CPU row. Smoke is plumbing only; long measurement remains queued.
