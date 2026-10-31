# PROPOSED recovery envelope for fresh MAIN and OWNER review

Actual old job failed rc1 at its first status query: supervisor rc64 stderr
`query denied: source clone contains a symlink`. Original seven fixtures passed.
Native `git ls-tree` proves both refused links are tracked mode120000 blobs in
ORCH43. Original source accepted seal c07a5a01, envelope ab07fe1d, old runtime
results, original private index/registry/DB/scripts remain untouched.

This separate recovery root proposes the narrow copy_source_tree correction in
source/SOURCE-PROPOSAL.md: exactly two path+target pairs become regular Git link
text; unknown/changed/missing links and special files fail. No target traversal.
Unchanged snapshot checks require fully symlink-free0555/0444 private view. No
native/runtime ptrace, argv, startup, mapping, canonical admission or library
policy relaxation. Mechanical source-root rebasing prevents the recovery from
writing old source runtime outputs. Six focused fixtures extend original seven.
Fresh fixture/syntax execution is NOT_RUN and is first inside a future grant.

NEW source digest b4c1414eccc2b8987d8f2b3eaa397f0b10438bd77d39487e7fd58c9ee7e30bbc
requires fresh OWNER-ACCEPTANCE.json and MAIN-APPROVAL.json at source/. Existing
approvals do not carry over. Unsigned templates exist; actual approval files do
not. Both signatures bind exact manifest digest and A_ptrace_event_admission.
They are external authority, excluded from source/envelope content hashes; the
sealed proof controller checks their exact digest, policy and accepted/approved
booleans before any fixture/native spawn. MAIN separately approves SHA256 of
packet/PACKET.sha256 via actual packet/MAIN-APPROVAL.txt. No such file exists.

SOURCE.sha256 preserves every old non-R2 external closure row unchanged, then
pins all13 new source members, new manifest and the two unsealed negative probes.
Body verifies all rows first inside the real grant. The old indexed source remains
43c63034432b6159fc503dc46c4671968514e7c5 with86116 nodes/160544 edges. No clone,
analyze, package install, shared database mutation or production tree work occurs.
Inherited closure bytes have not been re-executed or tested during preparation.

Only literal primary0-23 is accepted, checked in shell guard and Python gate;
launch command uses literal `taskset -c 0-23`. New ID is
codex-ni-gnx-r2-nativeproof-recovery1-20261026, min600/request900 seconds,
CPU/build/threads24, aggregate sampled RSS16GiB, no GPU. New own STOP and results
are bound to this recovery packet. Canonical own grant/bytes/window/deadline,
HOLD/quiet flags, own ended/complete and real guard locks remain mandatory.

Official launch remains launch.sh -> filler_run9 -> guarded body.sh -> proof.py.
Main proof behavior is unchanged except new root/source seal/ID and literal mask.
Firstgrant: hash provenance, Bash syntax, Python syntax/controller identity and
13 synthetic fixtures. Then status/context/impact, native read-only CREATE
rejection, CJS/ESM unsealed-source rejection, exit0-before-READY, stopped overflow,
forbidden exec, captured live affinity narrowing, in-grant deadline expiry,
captured supervisor kill with EXITKILL disappearance before controller cleanup,
exact argv/env negatives and optional owner-only own-grant revocation LAST.

Ordinary/lifetime aggregate<=24 includes supervisor+one outer controller; report
controller overhead separately. Deliberate overflow can transiently create a
25th ptrace-stopped task before refusal before user code; no kernel task-count
prevention guarantee. Read-only private view, mapped native cap and full source
closure remain required. Deadline/RSS monitor is not kernel memory.max.

OWNER-REVOCATION-CONTROL.template.json and OWNER-WATCHER-CONFIG.template.json are
schemas only. Old WS58 watch466487 is tied to old grant/rendezvous. MAIN must
arrange NEW owner config/watcher that names this exact ID/new rendezvous/own grant
before creating actual optional control. Driver never writes canonical grants,
claims or HOLDs. Without exact optional config owner transition remains NOT_RUN.
A new accepted source/envelope is not itself a resource grant or registration.

Any unexpected failure preserves raw receipts and stops; no blind retry. Risk
labels HIGH/CRITICAL/UNKNOWN or degraded/missing layer stop dependent source/R4
work; fixed independent instrument controls remain. Final RESULT means raw
native evidence for MAIN/OWNER review, not acceptance/PASS. No R4, impact coverage,
ROOT enrollment, publication, poller or process arming is included now.

Explicit copy assumption: source private tree remains exclusively owned and
immutable through copy, as in original policy. The two static pinned links are
omitted without reading either target. Standard copytree is not an adversarial
TOCTOU-safe dirfd copier; concurrent parent/file replacement can traverse before
observation. Observed destination links refuse before chmod. No race-proof copy
guarantee is asserted. OWNER source review must assess this exact assumption.
