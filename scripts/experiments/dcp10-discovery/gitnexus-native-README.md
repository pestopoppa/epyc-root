# DCP-10 native GitNexus capture controls

`gitnexus_native.py` prepares the read-only capture instrument for the original
Python, C and C++ DCP-10 bases. It has no command-line launcher. The native
driver and container command have offline controls. No Ladybug database query,
GitNexus index build, ColGREP inference or score runs in those controls.

The original official ColGREP result sealed at
`f4ba555150a489036d8b79de3f26dc8b92f9074ec60efdddd82204ec1d8fc0e6` records three
build errors. The capture helper refuses it. The prospective request may bind
the explicit `dcp10-colgrep-native-20261118-r2` row by its future result hash.
That result has to bind the known original row, preparation and result lineage
and contain all three reconciled task outcomes and their sealed attempts. Seed
paths and order come from those attempts. A successful empty upstream attempt
reports `no_seeds` without opening a graph query.

## Input bindings

`capture(assets, request_sha, task_id, remaining)` is for a future admitted
caller. `remaining(cap)` enforces the allocator STOP and deadline. The caller
supplies the prospective digest of `assets/request.json` and archives the
returned record and exact raw stdout. The request seals the original pilot
request and lexical baseline hashes, producer source hashes, installed GitNexus
writer sources, runtime identity, the parameterized query hash, output schema,
upstream row and result hashes, and exactly the original three task bindings.
Each binding carries `base`, ordered `seed_paths` and `index_receipt_sha256`.
The base includes the canonical original root, pinned commit and tree, and
original issue query hash. Stage the upstream result and attempts in
`assets/colgrep/` and the byte-identical driver at `assets/gitnexus_native_worker.mjs`.

Each `assets/index-builds/<language>.json` receipt binds its task ID, base,
GitNexus source identities, build manifest hash, and the exact `lbug` and
`meta.json` hashes. `assets/index-builds/<language>.manifest.json` must match the
manifest hash. `assets/indexes/<language>/` must contain only the database and
metadata. Metadata binds `repoPath` and `lastCommit` and records zero embeddings.
The installed writer's `run-analyze.js` emits these fields. Build custody and
the procedure that produced the sealed manifest need independent admission by
the future caller. Stock `analyze` can update `.gitignore` and a global registry.
This instrument opens an already checkpointed index and has no index writer.

## Source and launch controls

The source gate checks installed GitNexus 1.6.1 bytes and the exact executable
Node bytes. The driver loads the pinned CommonJS entry of `@ladybugdb/core`
0.15.4 and its pinned relative JavaScript and native addon dependencies.
Installed `database.js` documents `readOnly` as its fourth constructor
argument and `autoCheckpoint` as its sixth. Installed `connection.js`
implements `prepare`, parameterized `execute`, and a query timeout. Installed
`query_result.js` exposes row counts, iteration, and close. The driver binds
the seed list with that API. It reads stored `CodeRelation.confidence` from
one-hop cross-file edges and emits endpoint identities and paths. The
GitNexus pool attempts to load and install extensions, and the backend impact
flow can supply confidence when the stored value is absent. The driver uses
neither path. Graph output carries no line spans.

The pinned Docker image has a read-only root, no network, no host home, no
registry and no checkout mount. Only explicit node, driver, Ladybug and index
inputs are mounted, all recursively read-only. A missing image, unsafe writable
ancestor, runtime hash drift, untrusted task path, or index drift refuses the
capture. The original RAID scratch is currently under a peer-writable ancestor
and cannot satisfy mount custody as-is. No WAL or lock file is admitted. Any
Ladybug open failure is an error. Read-only open and ABI compatibility inside
this image still require a separate isolated qualification.

The query requests at most 4,097 rows to detect overflow of the 4,096-edge cap.
The driver also bounds serialized stdout to 4 MiB. Exceeding either bound fails
the whole capture. Successful empty edges are reported as `empty`. Query
failure is `error` and never supplies edges. Mount and source identity failures
stop the caller. The helper rechecks base, index and source identities after
query success or failure. Subsequent comparison, actual rendered capture,
trusted score admission and the existing verifier remain separate prerequisites.

## Private index producer

`gitnexus_build.prepare(assets)` seals a new request in an empty owned 0700
asset directory and returns its hash. It binds the original three base/query
identities, builder/capture sources, pinned runtime and a full inventory of the
installed GitNexus package including transitive modules and native parsers.
External package symlinks and special files are refused. This preparation does
not build an index. An admitted row caller then invokes
`build_private_index(assets, request_sha, task_id, remaining)` for each original
task, with its allocator STOP/deadline callback. Never call the builder outside
an admitted row or its publisher smoke.

The builder uses the pinned ingestion pipeline and database writer directly.
It bypasses stock analyze's registry, `.gitignore` and AI-file writes. The
original base, installed package, Node and worker are mounted read-only in the
pinned image with no network; only the new task output directory and bounded
scratch/home tmpfs mounts are writable. It inherits assigned CPU affinity and
caps the build at four CPUs, 8 GiB and 256 PIDs. A named container is removed on
success, error, timeout and termination; source and all original bases are
rechecked before any receipt is returned. A failed attempt cannot be reused.

The worker requires exact parsed-graph/database node and relation counts, zero
embeddings, an explicit checkpoint and close. Any stderr diagnostic, nonzero
exit or leftover CSV/WAL/lock/other sidecar refuses admission. It does not delete
sidecars to make admission pass. Successful output is placed directly under
`assets/indexes/<language>`; matching manifests and receipts under
`assets/index-builds/` are accepted by the existing capture reader. The
manifest records the prospective request hash, exact launch, source/base pins,
return code and output stream hashes. It contains no copied source or binary.

Offline controls exercise this orchestration with synthetic database markers;
they do not prove native database compatibility or runtime resource sufficiency.
The original shared RAID ancestry still fails the existing custody policy.
A row must arrange admitted private mount ancestry before qualification; do not
weaken that check. The installed adapter attempts VECTOR extension loading,
which may emit a diagnostic in the offline image and fail admission. Native
qualification must resolve that explicitly rather than suppressing diagnostics.
No private index has been built by these controls, and no graph score or
retrieval-quality result is claimed. The existing
`VB-CONTEXTBENCH-DISCOVERY-WIRE` source covers this producer.

## Allocator build qualification (2026-11-18)

`gitnexus_build_row.py` is an **unqualified candidate**, not an admitted launcher.
Its publisher smoke stopped before worker startup three times (Docker rc 125):
recursive mount propagation syntax, then descriptor-backed file/output mounts.
`dcp10-gitnexus-build-20261118` is not published and its lineage is parked under
the three-failure rule. Do not retry it or reset its failure count. Native ABI,
unused-extension handling, graph integrity and checkpointing remain untested.
See `docs/research/dcp10-gitnexus-build-qualification-20261118.json` for original
paths/hashes and the failed-qualification verdict.

The revised builder supplies ordinary canonical directory paths to Docker;
`/proc/<pid>/fd` is never a bind source. `pinned_mounts` applies the capture
helper's strict custody policy before opening descriptors, then compares named
and opened device/inode identities before launch and after container teardown.
Descriptors detect replacement and close on failure; they do not authorize a
peer-writable ancestor or make a shared path safe. Duplicate inputs close their
extra descriptors. Recursive read-only mounts retain explicit `rprivate`
propagation. The output is the only writable bind.

The bookkeeping-only shared-scratch exception in `check_build_path` cannot
admit a Docker mount. Existing request/base paths under shared scratch therefore
fail closed before Docker invocation. A future qualification needs an ordinary
path layout with trusted ancestry for **every** mounted directory (installed
source, original base, runtime, producer and output). Do not chmod shared
ancestors, silently relocate bases, substitute source trees, or copy checkouts
to evade this requirement. Bind any approved layout and original identities
prospectively before publishing a new qualification lineage.

The source-checked adapter variant omits VECTOR installation (no embedding arm),
sets a 1 GiB database buffer and four query threads. Installed source is never
modified and diagnostics still reject receipts. **34 offline GitNexus controls**
pass, including ordinary-path emission, descriptor cleanup, replacement refusal,
shared-ancestor refusal and refusal before Docker launch. Ruff passes. These
checks do not establish native Docker compatibility, ABI or checkpoint behavior;
no worker or graph build ran for this redesign. The parked lineage and the
capture helper's custody/source-admission refusals remain unchanged.
