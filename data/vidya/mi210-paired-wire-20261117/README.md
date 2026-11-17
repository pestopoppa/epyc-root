# MI210 prospective native patch packet

Prepared against the exact NPD1-STEP3 and Q38P-3a producer files named in
`manifest.json`. The `.original.py.txt` files are pinned source snapshots, not
measurement evidence or runnable successor jobs. Source and patched SHA-256s
allow the owning inference session to reject source drift before applying either
patch. No canonical producer, launch script, grant, or compute state was changed.

The patches import repository helpers through an explicitly supplied
`MI210_BELIEF_ROOT` (absolute checkout root, required even under Python `-I`).
They record a fresh `belief-<uuid>/` declaration before launches and retain
per-attempt native requests, errors, release, actual placement when observed,
residency/linkage evidence when observed, and terminal state. The optional
`MI210_BELIEF_GRANT` names a grant artifact whose bytes are hashed; omission stays
null. Missing build, model-shard and source-commit evidence stays explicit.
Native producer source bytes are hashed and verified before declaration creation.
Declared build paths are accompanied by current executable/library byte hashes;
path names are never treated as proof of a source commit. Q38 declared arm
metadata remains separately labelled as declared identity.

NPD1 retains complete native timings and sampled process affinity before and
after the request; those samples are not claimed to prove in-request linkage.
Its completion marker now goes to the selected output directory, including
smoke mode. Q38 retains the full native timing dictionary and writes invalid
units before returning. STOP, deadline, dependency refusal and exceptions all
close the raw capture or leave an observable interrupted record on hard death.
The Q38 smoke declaration names only its one actual planned launch.

`mi210_paired_raw.project(root)` accepts only complete measurement-scope captures
and projects individual native requests through the existing measurement carrier.
It supplies an empty protocol ID: these are diagnostic observations, graded by
`claim_tuple.grade()` as `Judged/Located`, never protocol attestations. NPD1 TPOT
uses lower-better; Q38 decode rate uses higher-better. It derives no ABBA effect,
causal explanation, or adoption decision. Failed/partial/stopped/smoke captures
remain readable raw records but do not project as complete measurement runs.

Validation applies each patch to its pinned snapshot in a temporary directory,
checks the resulting digest, and executes native control flow with fake inference
functions. These tests launch no kernels, servers, or compute jobs:

```bash
python3 -m pytest -q tests/vidya/test_mi210_paired_capture.py tests/vidya/test_mi210_native_patches.py
```

The source is not yet wired: application by the producer-owning session and a
planning-context canary remain necessary. This packet provides no historical
backfill and grants no permission to launch inference or modify production.

The private Q38 successor is now staged by
`scripts/vidya/producers/mi210_native_deploy.py`; `deployment.json` records
source, prepared model/build and deployed helper digests. It uses the restored
C5 image rather than the historical objcopy-rewritten image, with both identities
kept distinct. Model hashes are prepared before publication; execution checks
the prepared metadata and source seals without rehashing weights. The staged
helper bundle survives lane retirement and changes no canonical producer.

Row `vidya-mi210-q38-native-wire-20261117` was published on 2026-11-17;
`publish_row.py --smoke-now` reported **GPU busy, smoke queued**. No smoke
PASS, native capture or planner acceptance follows from publication. The
offline control `tests/vidya/mi210_native_deploy_control.py` verifies isolated
Python imports, wrong-width and altered-grant refusals and 20 synthetic
`Judged/Located` projections. Its fixtures are not native measurements.
