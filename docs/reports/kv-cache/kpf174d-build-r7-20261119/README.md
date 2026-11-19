# KPF-17.4d R7 build prerequisite

Row `kvu-kpf174-custody-r7-20261119` supersedes the failed R6 full build.
Source remains detached `6ec877068936588b6d63dbba5842bbd540b92031`, parent
`84d0a31603d495377dee24e1159bbbf02f1e2f21`; reference compiler/build options,
all eight binary/library receipt checks, compiler reopening, and linkage-helper
pin remain unchanged. This is a prospective build, not the historical image.

## Repair

R6's build log (SHA-256
`76fa1bd4ef25b11acf97e4807b2ca6402ee235aa7cfd1199aab063f9bd344383`)
records npm's engine refusal, HTTP failure for `b10350`, fallback to `latest`,
and the pinned embedder rejecting missing bundle/Workbox filenames.
R7 uses the compatible published `b10303` UI archive, fetched before publication:
`https://huggingface.co/buckets/ggml-org/llama-ui/resolve/b10303/dist.tar.gz`.
Its published checksum is
`9f692b00f9e52b939852a3045752395f2b8f0495063a26e4641a1a189478ae40`.
This pin identifies UI assets only; it makes no kernel-equivalence claim.

The task recipe is `scripts/benchmark/kpf174d_build_r7.py`. It verifies the
existing R6 preparation script (blob `64ccbd1c7b5fc71a85409a5297d6f221c4c0743a`),
the sealed R5 runtime list and source bytes. It stages the checked UI archive
in a fixed prepared build directory before publication, refuses paths escaping
the directory and nonregular archive entries, and pins every asset's digest and
metadata in the runtime-sealed `input/PREPARED.json`. No source tree is copied
or modified. The pinned CMake script accepts the fresh prepared outputs before
npm or network fallback; generated gzip files are excluded from input inventory.
Grant-time integrity checks reject changed/missing/extra inputs. Receipts retain
the UI input pins alongside unchanged source and reference-option custody.

The publisher smoke compiles the real KV-cache first object **and** runs the
source-bound `llama-ui-assets` target. Its receipt and completion reopen the
embed log and generated `ui.cpp`/`ui.h` as well as the first-object files.
This closes the UI failure path missed by R6's first-object-only smoke.
Full build, native linkage, knobs and custody acceptance still require the row.

## Reproduction

Scratch root:
`/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-build-r7-20261119`.
Create its detached `source` worktree at the commit above, download the archive
to `input/ui-assets.tar.gz`, then run `python3 scripts/benchmark/kpf174d_build_r7.py`.
The preparer refuses an existing spec. Publish the generated `spec.json` with
`python3 scripts/coordination/rowflow/publish_row.py <scratch-root>/spec.json`.
Source/input byte checks occur before publication, not during the grant.

Model-free mutation control: changing the fingerprint returned for staged
`index.html` produces `UI asset metadata changed: index.html`; unchanged prepared
inputs pass. Shell syntax and `git diff --check` pass. GitNexus status/impact
could not run because this worktree has no index; the changed code is a new
task recipe, with no daemon, fleet coordinator or production kernel edits.
No model loaded, historical re-judgment or full-build verdict follows.
[no-belief: build qualification only]

## Publication checkpoint

Publisher accepted the spec on 2026-11-19 and **queued** its smoke for the keeper.
It has not reported PASS; this checkpoint claims no native qualification.
The keeper owns smoke scheduling, and the session must consume its result on
resume before calling the row ready. Repair changed inputs on failure; do not
reuse an R6 smoke result. Full build still needs a later grant.

Prepared pins:
- `spec.json` SHA-256 `61eca06946b74d4cbf3013e7bfb117852110a387466f5cd72a45f3b35863631c`.
- `v3/launch.sh` SHA-256 `1228515a930467be47b69bd64802a9f8a511b901b08ef5530b6ccecbe60343b9`.
- `v3/runtime.sha256` SHA-256 `0fa24eac912a94e270e55fb62f0bb2395f065b956bb65ccb4f974fe0e81f8c61`.
- `input/PREPARED.json` SHA-256 `02921950f82b9f10131ee3c6d6f7ca4fadb4b638b19c9ede739d89e4191c2468`.
