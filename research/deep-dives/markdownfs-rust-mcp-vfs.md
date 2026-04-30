# markdownfs (mdfs) — Deep Dive

**Source**: https://github.com/subramanya1997/markdownfs (master branch, v0.2.0)
**Intake**: intake-520
**Date**: 2026-04-30
**Author**: Subramanya N (sole contributor)
**License**: MIT (declared in README; `license` field absent from Cargo.toml and GitHub API metadata — minor inconsistency)

## TL;DR

A 17-day-old, single-author Rust crate (8 commits, no published releases) implementing an in-memory virtual filesystem restricted to `.md` files, fronted by three independent binaries (CLI/REPL, HTTP/REST API, MCP server) sharing a single `MarkdownDb` core. Engineering quality is unusually high for a solo project this young — 239 tests, rigorous self-audit doc, current toolchain (Rust 2024 edition, axum 0.8, rmcp 1.4) — but the project has hard architectural ceilings (single-writer state file, 10 MB max file, 1 M max inodes, MCP runs as root) and just pivoted (2026-04-29 commits "Remove remote workspace stack" + "Remove Cloudflare deployment path"), narrowing scope from cloud product to local agent workspace. **For the EPYC stack the value is not adoption** — Git + planned KB-RAG + GitNexus already cover the same surface — **but two architectural patterns from its docs (`/runs/<run-id>/` markdown artifact schema, "filesystem truth + derived vector index" with heading-aware on-commit reindex) are worth borrowing into autopilot run records and validate our `internal-kb-rag.md` design respectively.**

## Project Snapshot

| Field | Value |
|---|---|
| Created | 2026-04-13 |
| Last push | 2026-04-29 |
| Total commits | 8 |
| Default branch | `master` |
| Stars / forks / watchers | 169 / 9 / 0 |
| Open issues / PRs | 0 / 0 |
| Repo size | 237 KB |
| License | MIT (README); not declared in Cargo.toml |
| Toolchain | Rust edition 2024, MSRV not declared |
| Topics on GitHub | none |
| Releases | none published |

**Commit history** (full):

```
2026-04-29  1b96fda  Remove remote workspace stack
2026-04-29  3665b7d  Remove Cloudflare deployment path
2026-04-29  30e87fb  Update mdfs examples and aliases
2026-04-28  4d411f4  Add remote workspace and POSIX support
2026-04-13  41f66c6  Add home directory auto-creation, improve first-run UX, add docs
2026-04-13  6a85225  Production database: concurrent core, HTTP API, MCP server
2026-04-13  f792c5b  Multi-user permissions, comprehensive tests, modular test structure
2026-04-13  3aa175d  Initial commit: mdvfs — markdown virtual file system
```

The project went from initial commit to "production database" in one day, then sat for two weeks, then in a 24-hour window added a remote/Cloudflare deployment path and immediately removed it the next day. That arc reveals an active scope-finding pivot from "remote/cloud markdown FS" to "local agent workspace." The current product surface should be read as the post-pivot intent.

## What It Actually Is

`mdfs` is **not** a filesystem in the Linux/POSIX sense. It is an in-process Rust library (`MarkdownDb`) wrapping a `BTreeMap`-style inode table, a content-addressable object store, and a Git-style commit log, with three binaries that wrap the library:

| Binary | Purpose | Auth model |
|---|---|---|
| `markdownfs` | Interactive REPL (rustyline) | Multi-user with `wheel` group, `su`, chmod/chown, agent tokens |
| `mdfs-server` | HTTP/REST API (axum + tower-http) | `Authorization: User <name>` or `Bearer <agent-token>` |
| `mdfs-mcp` | MCP server over stdio (rmcp) | **None — all operations run as `uid=0` root** |
| `mdfs-mount` | Optional FUSE mount (feature `fuser`) | Inherits caller's session |

All four bind to the same on-disk `.vfs/state.bin` (atomic bincode serialization, single file). The CLI and HTTP server cannot run concurrently against the same data directory — see [Architectural Limits](#architectural-limits) below.

## Source Layout

```
src/
  lib.rs              (public API surface)
  main.rs             (CLI/REPL binary, 8.3 KB)
  db.rs               (MarkdownDb: Arc<RwLock<DbInner>>, 18.7 KB)
  config.rs           (env-var-driven config)
  persist.rs          (atomic bincode save/load, 8.2 KB)
  fuse_mount.rs       (FUSE binding when fuser feature enabled, 17.7 KB)
  posix.rs            (POSIX semantics layer, 9.5 KB)
  error.rs            (VfsError enum)
  fs/                 (VirtualFs core: inodes, path resolution, all ops)
  store/              (content-addressable object store)
  vcs/                (commit, log, revert)
  auth/               (User, Group, UserRegistry, perms, sessions)
  cmd/                (CLI command dispatch + Unix-style pipes)
  server/             (axum routes: routes_fs, routes_vcs, routes_auth, middleware)
  bin/                (mdfs_server.rs, mdfs_mcp.rs, mdfs_mount.rs)
  io/                 (likely streaming / chunk helpers)

tests/
  integration/        (111 tests)
  permissions/        (72 tests)
  perf/               (37 perf benches)
  perf_comparison.rs  (1 test, 35.5 KB — the "102.8×" benchmark)
```

**Dependencies (Cargo.toml)**: `tokio` (full features), `axum` 0.8, `tower-http`, `rmcp` 1.4 (server + transport-io), `rustyline` 15, `serde` + `serde_json`, `bincode` 1, `sha2`, `memmap2`, `regex`, `glob`, `chrono`, `clap` 4, `thiserror` 2, `tracing`. Optional `fuser` 0.17 behind a feature flag. **No DB engine** — everything is custom data structures + sha2 for object hashes + bincode for persistence.

## Decoding the "~102.8× average speedup over native filesystem" Claim

This number is the headline of the README and the most likely thing to be misread. The full source is in `tests/perf_comparison.rs` (1,035 lines). Reading it carefully:

**Methodology**:
- 16 micro-benchmarks across `touch`, `mkdir -p`, write-small, write-large, overwrite-same, read-many, read-hot, `ls`, `stat`, `grep -r`, `find`, `rm`, `mv`, `cp`, save/load, plus VCS commit/revert/dedup (no native equivalent).
- Each bench runs the operation against `markdownfs` (in-process Rust) and against `std::fs` operations on `std::env::temp_dir()` (typically `/tmp` — **on Linux this is tmpfs by default, i.e., RAM, not NVMe**).
- Per-op timing: total elapsed / N operations. No warm-up, no statistical envelope, no percentiles.
- "Average speedup" = arithmetic mean of `native_µs / mdfs_µs` across the comparable subset (~14 ops).

**What is actually being measured**: in-process function call + RwLock + BTreeMap mutation **vs** kernel syscall round-trip + VFS layer + dentry cache + tmpfs page allocation. For tiny per-op costs (single-byte writes, single-file stats), the per-call kernel overhead dominates. So the speedup is real and the number is reproducible, but it measures **kernel VFS / syscall overhead saved**, not "in-memory beats disk."

**Per-op character (qualitative — extracted from bench structure, not numeric runs)**:

| Operation | Likely speedup regime | Why |
|---|---|---|
| `cat` same hot file (100 K×) | very high (100–1000×) | mdfs returns reference into in-memory buffer; native must `read()` syscall + page-cache lookup |
| `touch` (create 10 K files) | high (50–500×) | inode allocation + dentry insertion in tmpfs vs HashMap insert |
| `stat` (10 K×) | high (50–500×) | metadata syscall vs struct lookup |
| `mv` (1 K renames) | medium (5–50×) | both are O(1)-ish; kernel rename has dentry locking |
| `grep -r` (1 K files) | low–medium (3–20×) | both must scan content; mdfs avoids open/close per file |
| `write` 10 KB (1 K files) | low (2–5×) | actual content size matters, both eventually `memcpy` |
| `save` 10 K files | high (~50×) | mdfs writes one bincode blob; native writes 10 K separate files |
| `load` 10 K files | medium | one mmap'd binary vs 10 K opens |

**Implications for EPYC**:
- The benchmark says nothing about workloads where the FS isn't a hot path. EPYC's bottleneck is LLM inference (multi-second per turn, ~50 t/s decode); markdown filesystem ops happen at human/agent timescales and are nowhere near saturating syscall throughput.
- For the `wiki/` + `handoffs/` corpus (~150 files), the difference between mdfs at ~10 µs/op and tmpfs+git at ~100 µs/op is invisible against a single inference turn.
- Where it would matter: a future scenario where the orchestrator does ≥100 K markdown ops/sec on a single agent's working set. We have no such workload, and if we did, the right answer would be a `HashMap<Path, String>` in-process — the very thing mdfs is, but without the constraint of being sole writer of `state.bin`.

**Verdict on the headline**: the 102.8× number is technically correct, methodologically defensible, and substantively misleading as a value prop for EPYC.

## Architectural Limits (the original intake missed two of these)

These are documented inside the project, not external critiques.

### 1. MCP runs as root with no per-user auth

From `docs/mcp-guide.md` ("Important Notes" section):

> **All MCP operations run as root** (uid=0, gid=0). There is no per-user authentication within the MCP protocol — the agent has full access.

And from `docs/demo-readiness.md`:

> ### 3. Agent-scoped MCP auth — This matters because the current MCP server runs as `root`. […] Why it should follow soon after: Root-scoped MCP weakens the control-plane narrative.

**Implication**: the multi-user / `addagent` / bearer-token / chmod story is **HTTP-only**. The MCP integration — which is the most interesting hook for agent workflows — bypasses the entire permission model. The project's own positioning doc lists "agent-scoped MCP auth" as a known follow-up, not a feature. Anyone evaluating mdfs for "user-to-agent delegation" needs to read this carefully.

### 2. Single-writer per `state.bin`

From `docs/mcp-guide.md`:

> **Note:** Only one process can safely write to the same `state.bin` at a time. If you need concurrent access from multiple clients, use the HTTP server as the single point of access.

So the three frontends (CLI, HTTP, MCP) cannot share a workspace concurrently. Multi-process deployment forces every client through the HTTP server. The MCP server is intended for direct attachment to a single agent client (Cursor/Claude/etc.), not for multi-agent coordination on shared state.

### 3. Hard ceilings (configurable but real)

From the README's configuration table:

| Limit | Default | Comment |
|---|---|---|
| `MARKDOWNFS_MAX_FILE_SIZE` | 10 MB | Per file |
| `MARKDOWNFS_MAX_INODES` | 1,000,000 | Whole workspace |
| `MARKDOWNFS_MAX_DEPTH` | 256 | Path depth |
| `MARKDOWNFS_AUTOSAVE_SECS` | 5 | Crash window in seconds |
| `MARKDOWNFS_AUTOSAVE_WRITES` | 100 | Crash window in operations |

Auto-save is the durability boundary: a crash within the 5-second / 100-write window loses up to that much state. Acceptable for a workspace with explicit `commit` markers but not for general FS semantics.

### 4. `.md`-only by design

`touch foo.txt` is rejected at the syntax layer. The project is explicitly markdown-only and treats this as a feature, not a limitation. For our use case (markdown-heavy KB) this matches; for any orchestrator state surfaces (JSONL journals, npz/parquet retrieval indices, sqlite catalogs) it is a hard exclusion.

### 5. No multi-process / no distributed mode (post-pivot)

The 2026-04-29 commits removed "remote workspace stack" and "Cloudflare deployment path." The current product is single-host, single-process (with the HTTP server as the single-writer multiplexer). Anything multi-host requires the (now removed) remote stack.

## Engineering Quality (Better Than Expected)

Despite being 17 days old, mdfs has unusually high engineering hygiene for a solo project:

- **239 tests across 5 suites** — not a vanity number. `cargo test --release --test perf` finishes in 4.76 s, all 37 perf benches pass. 72 dedicated permission tests means the auth/perm path is genuinely exercised.
- **Self-audit document** (`docs/verification-report.md`, 385 lines): the author tested every CLI command and every HTTP endpoint against the documentation, found 1 medium-severity bug (`groups <other_user>` denied wheel members) and 6 doc/reality mismatches (auto-create parent dirs lie, list response schema, login response group format, test count, prompt visibility, revert-resets-cwd), then **fixed each one in-tree** and re-verified. The "Resolution status" section at the end shows commit-level traceability of fixes. This is rarer than 6 K stars on a project this young.
- **MIT-licensed in README**, but the `license` field is absent from `Cargo.toml` (and the GitHub API returns `license: null`). Minor governance gap — could trip a permissive-license SBOM check.
- **Rust edition 2024** + axum 0.8 + rmcp 1.4 — current toolchain, not stale.
- **Optional FUSE** — `fuser` is behind a feature flag, not a hard dep; macOS macFUSE compat included. Building without FUSE is the default.
- **Sensible env-var configuration** — every limit is overridable via `MARKDOWNFS_*` env vars.

## Documentation Maturity

11 docs in `docs/`, total ~85 KB of prose. Notably:

- `agent-workspace-positioning.md` (3,969 B) — explicit competitive framing against AWS S3 Files (announced as native filesystem for AI agents); a "Language to avoid" section reads as a self-imposed truth-in-marketing fence ("Runs arbitrary CLI tools today" — avoid; "Drop-in replacement for S3 Files" — avoid).
- `semantic-index.md` (5,720 B) — design doc for a derived vector index over the markdown workspace (see [Patterns Worth Borrowing](#patterns-worth-borrowing-into-epyc) below).
- `execution-roadmap.md` (4,273 B) — design doc for evolving from workspace into execution layer with a `/runs/<run-id>/` markdown artifact schema.
- `verification-report.md` (17,545 B — largest doc) — the self-audit described above.

The fact that two of these docs (`semantic-index.md`, `execution-roadmap.md`) are **forward-looking design docs without code** signals the author is consciously writing the spec ahead of the implementation. For our intake purposes the un-implemented patterns are the most useful, because they're decoupled from the (small, single-author, single-writer-constrained) implementation.

## Patterns Worth Borrowing Into EPYC

These are extracted from the documented design space, independent of whether we ever ship mdfs as a dependency.

### Pattern A — `/runs/<run-id>/` markdown artifact bundle (from `execution-roadmap.md`)

Reserved per-run directory layout:

```
/runs/<run-id>/
├── prompt.md
├── command.md
├── stdout.md
├── stderr.md
├── result.md
├── metadata.md     (agent_id, start_ts, end_ts, exit_code, workspace_id, source_commit)
└── artifacts/
```

**Contrast with our current journal-based approach** (`autopilot_env_synth_journal.jsonl`, halo trace format, etc.): JSONL records are agent-machine-friendly and queryable but human-illegible at scale. A per-run directory of markdown files would be human-reviewable, diff-able, search-able with grep, and committable as a single tree under VCS — at the cost of more inodes and slower bulk replay.

**Where this could land in EPYC**:
- **autopilot run records**: when AR-3 trial journals graduate from "log-everything" to "pick a few representative trials per cycle for human review," a `runs/<cycle-id>/<trial-id>/` markdown bundle is a low-effort way to make those trials inspectable. Companion to (not replacement for) the JSONL journal.
- **HALO trace bundles**: when halo-engine spike runs (per `meta-harness-optimization.md`), wrapping the report-and-input-spans pair in a per-trace markdown directory matches HALO's own emphasis on human-reviewable traces.
- **agent-world ETD synthesized tasks**: per-environment task directories with a stable schema would help the AW-5 EvalTower projection step produce reviewable artifacts.

This pattern does **not** require adopting mdfs. It is a schema choice, useable under git or any plain filesystem.

### Pattern B — "Filesystem truth + derived vector index" with on-write/on-commit/on-revert reindex (from `semantic-index.md`)

The doc spells out a principle that **independently corroborates our `internal-kb-rag.md` design** at the architectural level:

| mdfs `semantic-index.md` | EPYC `internal-kb-rag.md` |
|---|---|
| FS canonical, vector DB derived | git + filesystem canonical, FAISS/.npz derived |
| Heading-aware chunking (title / heading / subsection) | Heading-aware (split at `^#{1,3}`, with max-chars cap) |
| Metadata: workspace_id, file_path, heading_path, commit_hash, author, timestamp, perms | Metadata: file_path, heading_path, line_range, mtime, content_hash |
| Index update strategy: on write / on commit / on revert | Index update: PostToolUse-on-commit hook, content_hash diff |
| Query → semantic search → exact file open | Query CLI → ranked chunks with breadcrumbs → orchestrator reads file |

**Reading**: this is independent confirmation that the architecture in `internal-kb-rag.md` (K1–K7) is the canonical shape of "FS-truth + derived vector index" for markdown agent workspaces, and is showing up convergently across solo Rust authors and our own design. It does not change our plan, but it *de-risks* it — we are not on a private architectural branch.

### Pattern C — Heading-aware breadcrumbs in retrieval results (also `semantic-index.md`)

Output schema:

```json
{
  "results": [{
    "path": "/runbooks/payment-service.md",
    "heading": "Prior Learning",
    "score": 0.93,
    "excerpt": "..."
  }]
}
```

Compare to our K4: `[{file, heading_path, line_range, snippet, score}, ...]`. Equivalent. Useful as a sanity check on our K4 schema before implementation.

### Pattern D — `addagent` user class with token-once-shown-then-hashed semantics (`docs/user-management.md`)

```
alice@markdownfs:/ $ addagent deploy-bot
Created agent: deploy-bot (uid=3)
Token: a1b2c3d4e5f6...  (save this — shown only once)
```

The token is shown raw once; mdfs stores only its SHA-256 hash. Standard credential-handling pattern, but worth noting because:

- It distinguishes humans (`adduser`) from non-humans (`addagent`) at the identity-creation level. Conceptually parallel to our orchestrator distinguishing "skill" vs "user" actors, except mdfs makes it a first-class user type.
- For our orchestrator, where every actor is currently treated symmetrically, a typed `Agent` actor with token + permission scope is a cleaner identity model than the implicit "all callers are trusted" pattern we use today.
- Caveat: as documented above, this whole identity/permission system **does not extend to MCP** in mdfs. The pattern is good; mdfs's own implementation of it is incomplete.

## Where This Does NOT Help EPYC

To be explicit:

- **Not a substrate replacement for `wiki/` / `handoffs/`**. Git + planned KB-RAG + GitNexus already cover the role; the markdown-only restriction means it cannot replace any non-markdown state surface (JSONL journals, npz, sqlite); single-writer constraint means coexistence with any CLI tooling that touches the same files is awkward.
- **Not a perf upgrade**. The 102.8× number measures kernel VFS overhead saved, which is irrelevant for our LLM-inference-bound workload.
- **Not a multi-agent shared-state primitive**. Single-writer-per-state.bin and root-scoped MCP make the "shared durable memory across agents" framing aspirational, not implemented.
- **Not a versioning replacement for git**. Git already serves this role for our markdown corpus, with full multi-process safety, real branching, and 50× the test surface mdfs has.
- **Not safe to adopt as a load-bearing dependency**. Single author, 17 days old, 8 commits, no releases, just-pivoted scope, MIT-but-not-in-Cargo.toml. If we ever grew a real need, the right move would be to vendor the (small) crate or reimplement the pieces we cared about.

## Verdict (Revised, More Precise Than Initial Intake)

**worth_investigating, low-relevance, do-not-adopt-as-dependency**, with three concrete carry-overs that do not require adoption:

1. **Borrow `/runs/<run-id>/` markdown artifact schema** for autopilot/HALO run records as a complement to JSONL journals (Pattern A). Independent of mdfs.
2. **Treat `semantic-index.md` design as independent corroboration of `internal-kb-rag.md` K1–K7 architecture** (Pattern B). De-risks the design decision; no implementation change required.
3. **Catalog `mdfs-mcp` as one ETD candidate environment** for the AW-1 ETD agent's MCP-tool sweep (already noted in `agent-world-env-synthesis.md`). Note the MCP-runs-as-root caveat when scoring environment safety in AW-4.

**Watch signals**:

- If the project lands per-user MCP auth (`docs/demo-readiness.md` flags this as imminent follow-up), one of the most interesting design ideas — typed agent identity with permission scope at the MCP boundary — becomes implemented rather than aspirational. That would lift relevance from low to medium.
- If AWS S3 Files, mdfs, and similar offerings consolidate into a recognizable "agent workspace" product category, has implications for how `hermes-outer-shell.md` should position the EPYC orchestrator — currently we are inner-loop inference; the outer-loop "workspace" is being defined by the market.
- If mdfs publishes a release / picks up a second contributor / lands the run-records phase from `execution-roadmap.md`, the adoption-risk profile improves materially.

**Do NOT revisit** unless one of the watch signals trips. Current EPYC priorities (CPU optimization remediation, retrieval infra, autopilot species expansion) all have higher leverage.

## Sources Read

| File | Size | Used for |
|---|---|---|
| `README.md` | 9,778 B | Surface API, perf claim, configuration, MCP tool list |
| `Cargo.toml` | 1,241 B | Dependencies, binaries, feature flags |
| `tests/perf_comparison.rs` | 35,513 B | Decoding the 102.8× claim |
| `docs/verification-report.md` | 17,545 B | Engineering quality assessment |
| `docs/agent-workspace-positioning.md` | 3,969 B | Strategic framing, competitive context |
| `docs/semantic-index.md` | 5,720 B | Pattern B (vector index design) |
| `docs/execution-roadmap.md` | 4,273 B | Pattern A (run records schema) |
| `docs/demo-readiness.md` | 2,907 B | Self-stated gaps (MCP root-auth) |
| `docs/mcp-guide.md` | 6,831 B | MCP tool semantics, root-auth caveat, single-writer caveat |
| `docs/user-management.md` | 8,954 B (~120 lines read) | Pattern D (addagent), permission model |
| GitHub commit history | 8 commits | Pivot evidence |
| GitHub API metadata | — | Stars, forks, issues, license, age |
