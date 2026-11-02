# Q38-T7 isolated-arm coordinator

`q38_t7_isolated.py` and `q38_t7_runtime.py` are the prospective successor's
coordinator and runtime contract. They retain the original source in `q38_t7.py`
unchanged. The coordinator runs the drafted and no-draft arms sequentially,
requires verified cleanup between them, seals identical pair bodies, rejects
request-level speculative overrides, and sends each arm its own warm request.
For a cached measurement it requires a native cache count at least as large as
the predeclared threshold. The warm and measured messages must share the declared
prefix. Every response and request-body hash is returned, including on partial
failure; no Q38 quality or speed verdict is inferred here.

`q38_t7_payloads.py` constructs the original phase-A workload settings and
phase-B generation and needle settings from supplied frozen prefixes, scores
with the retained original grader and degeneracy detector, and renders the A/B
tables. It requires complete arm/request custody, matching body hashes, cleanup,
cache witnesses and response/tokenizer data; incomplete input is UNKNOWN and
missing timing makes speed invalid. The plan has its own content hash. Phase B
warms both servers independently, so those timings are a prospective protocol,
not the original shared-server historical timings. The supplied transport must
bind token IDs to the actual response and tokenizer and retain native streams;
the fake envelope used by tests does not establish this production proof.
`q38_t7_transport.py` now retains and hashes raw HTTP/SSE, requires a complete
stream, measures first text-event latency, and accepts a tokenizer-attestation
provider. The scorer re-parses stream evidence and binds the re-tokenized text
and token IDs to the plan's tokenizer digest. These IDs are re-tokenized output,
as in the original classifier, not server-native generation IDs. Missing or
mismatched provenance is UNKNOWN. The optional MTP table consumes hash-bound
historical rows and labels its arithmetic ratio as descriptive across different
cache protocols; it supplies no controlled comparison or promotion authority.

`OwnedHttpTransport` and `NativeTokenizerAttestor` use the captured child's
explicit loopback listener and verify native process/socket identity before and
after both response and `/tokenize` calls. Tokenization receipts retain the raw
server response and bind its token IDs to exact output text, PID/birth, model,
tokenizer and an external native-identity evidence digest. `run_attested_plan`
requires this transport and matching plan/recipe digests before the first
launch. One consistent process identity per arm and distinct arm processes are
required at scoring. Fake servers exercise the path end to end; they do not
prove a production model or tokenizer identity. The independently supplied
model/tokenizer, membership and mode verifiers still need real native evidence.

`q38_t7_journal.py` commits a model/cohort/arm/pair/kind/body exposure before
dispatch and retains the response or transport error afterward. Reopening the
same canonical SQLite database refuses an exposed or completed identity; the
same measured body/model/arm is also refused under a changed cohort. Distinct
declared warmup cells can share a body. Rowflow must bind and retain this one
canonical database: replacing it or changing a model pin is outside this
ledger's no-redraw guarantee. A STOP after the durable pre-dispatch record is
conservatively exposed even if no request was sent. STOP is checked before
dispatch, between HTTP reads and before/after tokenization; retained partial
bytes are journaled and the coordinator drains its captured child. A blocked
network read is bounded by its configured timeout and is not interrupted by the
STOP poll itself; production STOP responsiveness still needs qualification.

`test_q38_t7_isolated_http.py` starts two **fake** HTTP server subprocesses in
sequence, routes real local HTTP calls, and verifies independent warmups,
matching body hashes, correct arm modes, refusal on mismatched mode or cache
evidence, and cleanup of its captured children. This exercises coordination,
not production serving or inference.

`q38_t7_supervisor.py` owns a captured subprocess using its PID, birth time and
pidfd. It builds separate recipes, checks pinned binary/model/draft digests,
rejects draft options and inherited llama/draft variables in the common recipe,
signals only its captured child, and requires a caller-supplied descendant-drain
verifier before reporting cleanup. The fake-HTTP test exercises this owner;
unverified cleanup remains sticky.

`q38_t7_native_verify.py` verifies captured birth identity and argv, pinned
executable and mapped-library hashes, no unpinned ggml mapping, and ownership of
the expected IPv4 loopback listener. Library pathname device/inode must match
the live mapping before and after hashing; this does not by itself establish
immutable same-UID file custody. It also checks an attested exclusive cgroup
has an empty subtree. Its membership, effective draft-mode and exclusive-cgroup
ownership attestations remain required external proofs; neither current cgroup
membership nor a fake test establishes exclusive custody or effective mode.

There is deliberately no production CLI, concrete cgroup-placement or mode
attestor, native model-identity verifier or durable journal. Before target use, implement and qualify those
against the host's child/descendant ownership, process and socket identity,
recipe/binary/model/library binding, STOP and drain, durable no-redraw exposure,
native cache receipts and rowflow contracts. `Runtime`'s injected verifiers
and journal must prove these facts; a URL, mode string, fake-process test or
boolean supplied without such a proof is not qualification. Phase C, native
scoring and the remaining runners are outside this slice. KVU-16h-runner stays
open, and the guarded entry point remains the only supported historical-Q38
entry until the full successor is qualified.
