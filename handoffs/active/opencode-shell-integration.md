# OpenCode Shell Integration — Phase 0

**Status:** active; dated r3 acceptance and card/release pin are recorded. Remaining P0 override carry requires its inference owner; P7 is source-only launcher work.
**Scratch:** `/mnt/raid0/llm/worktrees/ni08-screen-proposals-root-20261006`, `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`.
**Parent:** [harness-selection-and-integration.md](harness-selection-and-integration.md), which retains decision/candidates/P1–P6 gates.
**Owner index:** [user-facing-harness-index.md](user-facing-harness-index.md), UFH-15.

## Start here

Fix P7 prompt transport and its argv guard; validate the remaining `/v1` override carry only at the owning inference session boundary. The operator approved this split on 2026-09-17; its recorded P0.4 trigger passed on 2026-09-26.

## Phase 0 tasks

    - [ ] **HS-4 P0 — shell integration, zero features** (doc §4). Per-step state (boxes are ticked by the owning session at the P0.4 live gate; evidence recorded in text):
      - Closed (evidence in [completed sibling](../completed/harness-selection-completed-through-2026-09-27.md)): P0.1, P0.2, P0.3 (audit at 350c726a), P0.4 (live PASS 2026-09-26, r3), P0.5, P0-MCP-a/b, the P0.4 preflight install, and both P0-pre fixes.
      - Watch item (P0.3 audit): the v2 session runner /api/session/:id/prompt has no plugin hook, so x_* stamping does not reach it.
      - [x] **P0.4b — republish the Harness Card for this configuration (HS-7)** ([`harness-card.md`](../../docs/reference/harness-candidates/harness-card.md)): OpenCode `v1.18.31`, the plugin/config hash from the r3 `opencode.jsonc`, `x_tool_mode="client"`, the served role and build. Zero inference. Filed 2026-09-26.
      - [x] **P0.4c — freeze the OpenCode pin (HS-5b ordering: freeze before anything trains against the shell) at the RELEASE TAG `v1.18.31` = `014614d35b39`**, not at `350c726a`: the 2026-09-26 research intake (Stage 4) found `350c726a` is a dev-branch commit whose packages report 1.18.31, while the tag is what `npm install opencode-ai@1.18.31` installs and what r3 ran (`opencode --version` 1.18.31). Record `350c726a` as the audit anchor only. Zero inference. Filed 2026-09-26.
      - [x] **HS-4 P0.4 preflight follow-up — pin `opencode-ai@1.18.31` in `.devcontainer/Dockerfile`** so a container rebuild keeps the audited version (today the Dockerfile installs no OpenCode).
        ✅ 2026-10-06 — MAIN applied the exact npm package version after readonly official registry verification; no container build or runtime installation claimed.
    - [ ] **HS-4 P0.4 carry — live `/v1` override validation, shell-agnostic** (moved 2026-09-16 from the closed [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) items Phase-2 and P; **needs inference**). In the P0.4 quiet window, run `scripts/hermes/reference_openai_client.py --send` (print-only by default) against the current `/v1/chat/completions` and verify: role override, `x_force_model`, `x_max_escalation` (still metadata/pass-through on this route until full-graph enforcement; see P4 routing parity), `x_disable_repl` end-to-end, `x_show_routing` metadata, and streaming with the override params present. Procedure: [`client-surface-audit.md`](../../docs/reference/harness-candidates/client-surface-audit.md) Step 4.
      ✅ 2026-10-06 — MAIN reopened original r3 source/config/receipt objects, republished the dated HS-7 card and froze release tag `v1.18.31`=`014614d35b397775e5d397a490fc72368c894ec2`. [Review](../../artifacts/ni08/harness-phase0-source-20261006/README.md). No new inference.
    - [ ] **HS-4 P7 — OpenCode re-quotes any positional containing a space; pass prompts on STDIN.** opencode 1.18 builds its message as `message.map(G => G.includes(" ") ? '"' + G.replace(/"/g, '\\"') + '"' : G).join(" ")` (verified in the 1.18.31 binary) — the DS41 2026-09-24 planner prompt reached the model wrapped in quotes with 2,982 backslash-escaped quotes, all JSON. Stdin is appended verbatim (`message + "\n" + stdin`) and also clears the kernel's 128 KiB per-argument limit (~100 KB prompts). Reference fix: research `loop/actors.py` `Backend.argv` for `opencode` + `Backend.stdin_payload` (lane `lane/ak-actor-seat-20260924`). Action: audit every place this repo invokes `opencode run` / a CLI shell with a prompt argument (`scripts/hermes/`, any launcher under HS-4) and switch to stdin; add a guard test that the argv never carries the prompt. Zero inference. The full list of measured `opencode run` headless pitfalls (stdin, pipe truncation, agent `prompt` replacing the system prompt, compaction echo, rc=1 with a complete reply, `hidden`, unused `task`) is in [`opencode-p03-audit-20260916.md`](../../docs/reference/harness-candidates/opencode-p03-audit-20260916.md) → *Addendum 2026-09-24*.

## P0.4 r3 evidence identity for the proposed HS-7 card

The live-run producer/source was the private ROOT worktree at commit
`0ce7e11162631f25b445e84a233589c498be5d3a` (tree
`7e61b42e2f05a6159e1b70080f8843db87e10d5f`), as resolved from the r3 `run.sh` path and the still-clean source worktree during this review. The
tracked r3 evidence was filed in ROOT commit `5c053841cdd6cb73b5a48ef623074dbc00bc13aa` (tree
`43bded6421375ac241b8a2b55fbff5ac79086bcd`). Git object IDs identify the original bytes; SHA-256
values bind the relevant payloads. The tracked artifact commit records source metadata and output
receipts, not the untracked `/mnt/raid0/llm/tmp` source originals.

| Evidence | Tracked path | Git blob | SHA-256 / recorded identity | Supports |
|---|---|---|---|---|
| Realized OpenCode config | `artifacts/harness/hs4-p04-20260926-r3/opencode.jsonc` | `a0da4052f7d54cfbf7246f1ed115051d0ffe64b4` | `e180a37d602f82b6f42e7d1a0f796c904075b9c532b1387657aebc80a17de4bf` | Exact r3 `opencode.jsonc`, plugin path and options, disabled MCP, shell permissions and autonomy settings |
| Captured version | `artifacts/harness/hs4-p04-20260926-r3/opencode-version.txt` | `769c5a4d057b2c98430169f166e2365f8d898536` | `ce93d3a23f487a3c7a9c41bcac7a01907e2d098e11d63d7d77187cb38add2af5` | `opencode --version` output `1.18.31` |
| Native shell-run sidecar | `artifacts/harness/hs4-p04-20260926-r3/opencode_shell_run.json` | `8d17bec1592fe780e1c0716a0b2e7357247938f2` | `85255c34ddb635a06891e4bfc34fe81c7dd18c68b684e9fdcfca111dc6d2da2b` | Harness audit pin `350c726aa8b6b11eb9242040bc5eb7ae837fbf8a`; config SHA; plugin package and SHA; request mode; role, build, endpoint; suite, arm, and denominator |
| Acceptance verdict | `artifacts/harness/hs4-p04-20260926-r3/verdict.json` | `fe295e0aecfc5056211e5c14faf55c48cdcb2450` | `7b5578a93887194dd04690169fa5cc0a25007d823d6f508c10a8f36ccbbc2c5b` | Live P0.4 acceptance passed; exact checks, including client keys, served token agreement and version |
| Prepared input | `artifacts/harness/hs4-p04-20260926-r3/prepared.json` | `7ee12d0110d56d046c6077094e515fe5ee4a112c` | `6a16d513dcf443d5a8b38055c0dd6d29f7a76d77fec18fc0ec3117d6d788df43` | Suite prompt metadata and pinned version claim |
| Attempt record | `artifacts/harness/hs4-p04-20260926-r3/attempts.jsonl` | `07cf52f502e71666238eeea8437dad99ae2f057d` | `e70c1ace7a21e2edbe9877ccc5e56f5324f5884487cf516e458bb23800afacb8` | One task, one attempt; evidence inputs and run completion |
| Captured belief rows | `artifacts/harness/hs4-p04-20260926-r3/opencode_shell_run.beliefs.jsonl` | `8feaaa0c4513d1687d25bca7a9bd0b8a7ea53083` | `ef872f17a1d8bf4aeb62802de70b3a2312317f1f693e1f35d9e34aba4dc360e7` | Plugin SHA and serving metadata projected with the native run record |
| Window start/end | `artifacts/harness/hs4-p04-20260926-r3/window-start.txt`; `window-end.txt` | `e519ff25b56a117bdfbd39fe41b635fc2ed77fcd`; `e5917f4c9ab729d5b1dec3d58ec7064ebdd2168b` | `c79781440f07d256268f12ddaaecdeded6d232cc8ae03f5935794a2cb9a06105`; `7d1d6464b989c4f989563bd4b5a893f652be05fcc5fa6cfbb294f4ce6250cbb6` | Captured run window |

The r3 `run.sh` points to the source worktree above, and the plugin path in its config resolves to
`harness/opencode-plugin/src/index.ts`. At producer commit `0ce7e11162631f25b445e84a233589c498be5d3a`,
the plugin tree is `73e5b468d9a4096f14eacd8f38b6665132b68fa4`; `src/config-lint.ts` blob is
`66f365760b2ceedba3f4770b2a22fd85d09895d4`, `src/index.ts` blob is
`99dd57bef8bafa58c742de70b569badcd8fb1e76`, and `src/lib.ts` blob is
`b16c4aec1959910c7a84e7f84b1de65a988e7207`. The same source tree and blobs occur in evidence
commit `5c053841cdd6cb73b5a48ef623074dbc00bc13aa`.

The producing source `scripts/harness/hs4_p04_acceptance.py` is blob
`50c06637f8a0fda2a2c085dcff5157f7ed834b7c` at producer commit; its `plugin_sha256()` definition
hashes sorted `src/*.ts` inputs with each filename and NUL separator included in the per-file
digest. The three source-file contribution hashes are `config-lint.ts`:
`e77fc5182aa7280e30400fbd41bf1a4c42e07859a56317923f0daaf7b5a5421d`, `index.ts`:
`89a7b314efc2dbf2edcd48da6a5567241bcac48f64f3321f1f1d4f0674214111`, and `lib.ts`:
`98b3e72f764cbf0edf7f7d2cdda6b6e1e65c5a117cfd317a415e64f51ffc7dc7`; the resulting digest is the
captured `d49194fcc50d66ff47afdc2aa12490b44579d25b316261843b949cb57edecfb1`. This ties the receipt
digest to the exact tracked source input set, not to one file.

The card's realized fields are therefore: package version `1.18.31`; install identity to freeze is
the release tag `v1.18.31` (`014614d35b39`), while the run's source audit anchor remains
`350c726aa8b6b11eb9242040bc5eb7ae837fbf8a`; config digest above; plugin name and digest above;
`x_tool_mode="client"`; served role `frontdoor`; build `b10303-ffc1bac82`; thinking disabled;
endpoint `/v1`; MCP disabled. The sidecar is `BASELINE`, one task and one attempt. Keep the r3 record
associated with its contemporaneous card version `HS-6@2026-07-29`; the new HS-7 card is the
disclosure for future realized-configuration reports. The one-run acceptance is not efficacy,
cross-harness comparison, or a general pass-rate claim.

