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
