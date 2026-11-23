# Dive — agentbench — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/THUDM/AgentBench/main/README.md", retrieved: "2026-11-23", sha256: "a5217fff33ac"}
> SOURCE-QUARANTINE: {url: "https://github.com/THUDM/AgentBench @ d1e4a10db08c (clone, reading material)", retrieved: "2026-11-23", sha256: "n/a"}
> SOURCE-QUARANTINE: {url: "https://github.com/THUDM/AgentRL @ 6a73409d31ba examples/eval/server_agent.py, docs/deployment.md", retrieved: "2026-11-23", sha256: "060d07a7dc56 / 122bb3cf5296"}

Bearing: intake-2856 (agentrl) ledger G2.

## 1. Stage-1 fields
AgentBench FC (function-calling prompts, containerized deployment); Xiao Liu et al. (THUDM); HEAD d1e4a10db08c, Apache-2.0, last push 2026-02-08. Categories: benchmark_methodology, agent_architecture, tool_implementation. Novelty low; relevance medium (substrate of G2 and LH4). Credibility 3 = within 12 months +1, known group +1, corroboration +1 (Life-Harness deploys the same controller). Verdict: adopt_component.

## 2. Key claims
0. **Stack. CONFIRMED.** Compose runs the controller (`jingbh/agentrl-controller:latest`, host network, :5020 per AgentRL docs), one worker per task, Redis, Freebase for KG (`extra/docker-compose.yml:6-8,87-89`). Images: `mysql:8`, three `local-os/*` builds; the ALFWorld worker builds from python:3.9, pulls three data zips from GitHub and pins CPU torch<2.0. Anchors 0-1.
1. **Resources. PARTIAL.** FC README: WebShop ~16 GB RAM; ALFWorld leaks memory and disk until its worker restarts. The table (alfworld ~10 s start, <500M) is in the v0.2 section. Anchors 2-3.
2. **"A worker can call a local OpenAI-compatible endpoint." NARROWED.** Workers never call the model. This repo's client (HTTPAgent) has zero tool-call handling, so it cannot drive FC. The driver is AgentRL `examples/eval/server_agent.py` (README path stale): `POST {-u}/chat/completions` with `tools`, `tool_choice: auto`, `max_completion_tokens: 1024`, temperature 0.8, model name from `{-u}/models` (lines 41-48, 159-165, 343). llama-server must return `tool_calls` (needs `--jinja`, uncited). Anchor 4.
3. **5-episode smoke. PARTIAL (wall time NOT-FOUND-IN-SOURCE).** ALFWorld `new_std` has 109 games, DBBench `standard.jsonl` 300 rows (data files); OS not counted. Step caps: ALFWorld 20, DBBench 15, OS 8 (task yamls); driver loop 20 turns (server_agent.py:118). Five episodes are at most 100 / 75 / 40 chat calls of <=1024 completion tokens. Select with `-r 0,5 -n 1 -j 1` (comma range, end exclusive, `-n` default 4; :216, 348).
4. **"Docker is the deployment." OVERTURNED for ALFWorld.** The controller is also a standalone Go binary, and Life-Harness runs it natively on loopback 15020-15023 with no-model smokes. `alfworld.yaml` needs no docker or Redis; DBBench and OS need Redis at 172.17.0.1 and a `docker.sock` mount (workers start sibling containers).

## 3. Reported results
None in source text (leaderboard is an image and a Google Sheet).

## 4. Performance-principles table
| Mechanism | MI210 | Zen 5 |
|---|---|---|
| ALFWorld text engine, controller, workers | n/a | YES, CPU only |
| Multi-turn prefix growth (ALFWorld prompt file 34,679 B before history) | YES: prefix reuse and small-ubatch verify matter | n/a |
| Worker concurrency 16/32 vs model slots | smoke uses `-j 1` | n/a |

## 5. In-house state
No ALFWorld, AgentBench or WebShop rows in the lane (`eval-tower-program.md` @ d785b6d). /usr/bin/docker exists; no redis-server on PATH. Upstream-present: n/a.

## 6. Derived-actionables ledger
| # | Task | Owner | Compute | Rule |
|---|---|---|---|---|
| AB1 | Refines agentrl G2: first smoke is ALFWorld only (controller + one worker, no Redis, no docker.sock) via `server_agent.py -u <llama-server>/v1 -c http://localhost:5020/api -r 0,5 -n 1 -j 1 alfworld-std`; DB and OS after it passes. | `eval-tower-program.md` | CPU row + one inference row | Done at 5 episodes with result and wall time; futility if the role returns no `tool_calls` (record template and flags). |
| AB2 | Add to G2 a build-identity rule: compose controller tag is `latest`; pin the release binary by SHA-256 or the image by digest and record it per run. | `eval-tower-program.md` | doc-only | Done when G2 names the pin. |
| AB3 | DECLINE: KG and WebShop workers. No ledger row consumes them (KG needs a Freebase database, WebShop ~16 GB RAM). | n/a | n/a | n/a |

## 7. Dive-surfaced sources
None change a row. Decline: AgentRL `controller-v0.2.0` release (asset of the agentrl entry); `alfworld/alfworld` (pinned in the Dockerfile).

## 8. Contradiction pass
Stale README path; unpinned `latest` controller; hardcoded 172.17.0.1; old HTTP client and FC configs coexist; ALFWorld leak admitted by the authors.

## 9. Read depth
PARTIAL: README, compose, three task yamls, three Dockerfiles, client, server_agent.py, deployment.md; OS/DB logic, KG, WebShop, controller source not read; nothing run. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e.

## Anchors (verbatim substrings of page.txt, verified)
0. `this version uses a function-calling style prompt, and adds fully-containerized deployment support`
1. `- AgentRL Controller - `alfworld` task worker (x1, increase as needed)`; `If your machine already has Redis (version 7+) running, you can omit the Redis service from the `docker-compose.yml`.`
2. `the current implementation of `alfworld` leaks memory and disk space until the task worker is restarted`
3. `| alfworld | ~10s | < 500M |`
4. `Fill in your OpenAI API Key at the correct location in `configs/agents/openai-chat.yaml`.` (old client). Claims 3-4 rest on repo files.

## 10. Artifact audit
artifact audit: clean
