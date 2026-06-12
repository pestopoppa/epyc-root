# Reboot validation + resume — picking up from 2026-05-16 session

## Closure note (2026-06-12, Fable 5 portfolio pass)

**Final outcome**: One-shot session-resume runbook whose steps were all carried out in the weeks following 2026-05-19: the four pre-reboot commits were pushed, the reboot happened, the isolation bench ran, the production stack restarted, and the autopilot relaunched (it has been running continuously since — trial ~777 as of this pass). The host-throttle finding it tested is canonicalized in memory `feedback_host_throttle_check` (tiered fix: ≥1wk uptime → REBOOT required, drop_caches insufficient — confirmed at 6d 18h) and `feedback_drop_caches_numa_eviction`.

**Why archived**: pure chronology — a 3+-week-old resume procedure with no live item. Nothing here is a standing protocol; the durable lessons live in the memory entries above and in `progress/2026-05/`.

**Where residuals now live**: the three "deferred until after this resume cycle" items were inherited by their owning handoffs at the time (`cmd_stop --all` traceback and `--compile-registry` default-on → orchestrator stack work; AP-28-31 wire-ins → `autopilot-continuous-optimization.md`); none are tracked here.

**Reopen triggers**: none — future reboot/resume cycles get their own runbook.

---

**Status**: Pre-reboot. All in-flight code + docs committed (4 repos, 4 commits) but not yet pushed. After your reboot, follow this handoff in order to pick up exactly where we left off.

**Created**: 2026-05-19
**Predecessor**: [autopilot-continuous-optimization.md §Session 2026-05-16](../active/autopilot-continuous-optimization.md)
**Progress entry**: [`progress/2026-05/2026-05-16.md`](../../progress/2026-05/2026-05-16.md)

---

## Why a reboot is the next step

The 2026-05-16 session resolved 4 user-prioritized items + same-GGUF consolidation + master registry reconciliation + a deep frontdoor throughput bisect. The bisect ended with one **residual unexplained gap**:

| Configuration | Decode t/s on Qwen3.6-35B-A3B Q8 |
|---|---|
| Bench retest 2026-04-20 (recorded in `qwen36_q8_0_retest_fork_fix.json`) | **26.0** ✓ clean output, 16/16 PASS |
| Current production binary, full stack, frontdoor in orchestrator | 12.50-12.66 |
| April 20 binary rebuilt + bench-recipe in TOTAL isolation (all other servers killed, 1068 GB free, fresh `drop_caches`) | 12.13-12.48 |
| April 20 binary, same prompt, same model md5 (`ae7e57fb…`) | 12.13-12.48 |

**The 2x gap survives every binary/config/isolation lever tested.** The host has been up 6 days 18 hours at session close. Per `feedback_host_throttle_check`: "sustained multi-day load can degrade throughput ~60%; PRIMARY FIX (2026-05-06): `sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches`". The drop_caches fix did NOT restore in this session — the throttle is now deeper than what drop_caches can address (the memory note "reboot no longer needed" may be incorrect post-multi-week uptime).

**Only untested lever**: reboot.

---

## Pre-reboot state — exact

### Repos with committed-but-NOT-pushed commits

| Repo | Branch | Commit | Push command |
|---|---|---|---|
| epyc-root | main | `ac2d899` docs(wrap-up): 2026-05-16 — autopilot recovery, gemma4 KMP_BLOCKTIME fix, registry compile, frontdoor bisect | `cd /workspace && git push` |
| epyc-orchestrator | main | `a98c2e4` feat(autopilot-recovery): KMP_BLOCKTIME, registry compile, host_health, same-GGUF consolidation | `cd /mnt/raid0/llm/epyc-orchestrator && git push` |
| epyc-inference-research | main | `58dd9ac` fix(registry): architect_general — model + acceleration reconciled | `cd /mnt/raid0/llm/epyc-inference-research && git push` |
| ik_llama.cpp | pr-1744 | `e01e6443` docs: KMP_BLOCKTIME note + params_use_gemma4_external_mtp simplification | `cd /mnt/raid0/llm/ik_llama.cpp && git push -u origin pr-1744` |

All four are 1 commit ahead of upstream (0 behind). Direct push to main was blocked by your hook during the previous session — push these manually from your host shell.

### Unstaged operational state (not session work — leave for owners)

- `epyc-orchestrator/scripts/autopilot/{failure_blacklist.yaml, short_term_memory.md}` — autopilot-auto-generated; will be touched by the next autopilot run.
- `ik_llama.cpp/src/llama.cpp` — Gemma4Assistant top-level tensor name handler (`mtp_pre_proj` / `mtp_post_proj` / `mtp_centroids` / `mtp_token_ordering`); not from the 2026-05-16 session. Leave alone or attribute via `git blame` to whoever wrote it.

### Stack state at session close

All 13 production servers running and healthy:
- frontdoor (8070) + coder_escalation + worker_summarize ALIAS → ONE Qwen3.6-35B Q8 server (consolidated)
- worker_general (8072) → gemma4-26B-A4B Q4 MTP with `KMP_BLOCKTIME=10` (verified 0 idle cores, threads sleeping on futex_wait_queue)
- architect_general (8083) → Qwen3.5-122B Q4_K_M, no spec decode (M-RoPE crash guard via `_NO_SPEC_DECODE`)
- ingest_long_context (8085), vision (8086), vision_escalation (8087), 6× embedders (8090-8095)
- orchestrator API (8000), sd_server (8190), document_formalizer/lightonocr (9001)

Autopilot **not running** (operator-controlled relaunch). Journal trials 314-322 (polluted by previous session) purged with backups at `orchestration/autopilot_journal.{tsv,jsonl}.bak-20260509-094821`.

---

## Resume procedure (post-reboot)

### Step 1 — push the four pre-reboot commits

```bash
cd /workspace && git push
cd /mnt/raid0/llm/epyc-orchestrator && git push
cd /mnt/raid0/llm/epyc-inference-research && git push
cd /mnt/raid0/llm/ik_llama.cpp && git push -u origin pr-1744
```

Run from a shell where your hook permits push-to-main. Verify each with `git log --oneline -1` after.

### Step 2 — verify clean boot state

```bash
uptime                              # confirm < 1 hour (verify reboot happened)
free -h                             # MemFree should be ~1.1 TB (no models loaded yet)
ps -eo pid,comm | grep -E "llama-server|sd-server|lightonocr|uvicorn" | grep -v grep
                                    # expect nothing — stack is down
sudo -n /usr/local/sbin/autopilot-flush-cache
                                    # cache flush sanity-check (should still say "drop_caches: ok")
```

Drop caches anyway to be safe (memory note says sync+drop_caches is primary fix, do it once after fresh boot too).

### Step 3 — single-server isolation bench (the hypothesis test)

Reproduce the bench retest recipe exactly, with NO other models loaded, on the production binary:

```bash
# Launch a SINGLE bench-recipe server on port 8099 with the EXACT recipe
# from epyc-inference-research/scripts/benchmark/run_qwen36_retest.py.
LD_LIBRARY_PATH=/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib \
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false \
  numactl --interleave=all \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
    -m /mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf \
    -t 96 --host 127.0.0.1 --port 8099 \
    -c 8192 --parallel 1 -ub 8192 -fa on -ctk q8_0 -ctv q8_0 \
    --jinja --reasoning auto \
    > /tmp/postreboot_isolation.log 2>&1 &

# Wait for ready
until curl -sf -m 1 http://127.0.0.1:8099/health 2>/dev/null | grep -q '"status":"ok"'; do sleep 5; done

# Smoke 5 samples
for i in 1 2 3 4 5; do
  curl -sS -m 60 -X POST http://127.0.0.1:8099/completion \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"The history of computing began with","n_predict":150,"temperature":0,"stream":false}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  run {$i}: decode={d[\"timings\"][\"predicted_per_second\"]:.2f} t/s')"
done

# Stop the test server
pgrep -f "llama-server.*--port 8099" | xargs -r kill -9
```

### Step 4 — interpret the result

| Result | Verdict | Action |
|---|---|---|
| **≥ 22 t/s** consistently | Host-throttle hypothesis CONFIRMED. The 26 t/s bench-era number is reachable on a freshly-booted host. | No code action. Proceed to Step 5. Schedule periodic reboots OR investigate what specifically the multi-week uptime degrades (kernel TLB? cpufreq pstate state machine? mglru?). Update `feedback_host_throttle_check.md` to reflect that reboot IS still needed for multi-week uptime. |
| **15-21 t/s** | Partial confirmation — host state contributes but isn't the full picture. | Further bisect: leave only frontdoor running, smoke. Then add one server at a time, smoke after each. Identify which co-resident process degrades performance even when idle. |
| **Still ~12.5 t/s** | Host-throttle hypothesis FALSIFIED. The 26 t/s number reflects something we cannot reproduce with current binary/model/recipe. | Deeper investigation needed: (a) re-fetch master Qwen_Qwen3.6-35B-A3B-Q8_0.gguf to verify md5 matches the bench era exactly; (b) compare /proc/cpuinfo / dmidecode / BIOS settings against `data/preflight/2026-04-20_*.json` snapshots; (c) consider that the bench retest JSON's `tokens_per_second: 26.0` may have been measured under conditions (TIDE drift, different physical machine, etc.) that we cannot now reconstruct. |

Whatever the result: record the decode t/s in `progress/2026-05/2026-05-19.md` (or whatever date) and update item 19a in `handoffs/active/master-handoff-index.md`.

### Step 5 — restart the production stack

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 scripts/server/orchestrator_stack.py start --numa-mode full --skip-host-prereqs
```

The validator gate (added 2026-05-16) will fire-fast on any registry inconsistency. Watch for `[registry-validator] FATAL` output. If clean, the stack should come up in ~2-3 min (sequential load per `feedback_sequential_model_loading`).

Verify health of all roles:

```bash
for p in 8070 8072 8083 8085 8086 8087 8090 8091 8092 8093 8094 8095; do
  printf "  port %s: " $p
  curl -sf -m 2 http://127.0.0.1:$p/health 2>&1 | head -c 80
  echo
done
```

Smoke test the consolidated frontdoor (which also serves coder_escalation + worker_summarize):

```bash
curl -sS -m 30 -X POST http://127.0.0.1:8070/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"x","stream":false,"max_tokens":50,"temperature":0,"messages":[{"role":"user","content":"/no_think Reply with: ok"}]}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); t=d['timings']; print(f\"decode={t['predicted_per_second']:.2f} t/s\")"
```

Verify the gemma4 KMP_BLOCKTIME fix is in effect (no idle spin):

```bash
GEMMA_PID=$(pgrep -f "ik_llama.cpp.*llama-server" | head -1)
# Wait 30s after stack ready (no traffic), then sample
read t1 < <(awk '{print $14+$15}' /proc/$GEMMA_PID/stat)
sleep 6
read t2 < <(awk '{print $14+$15}' /proc/$GEMMA_PID/stat)
python3 -c "print(f'gemma4 idle cores busy: {(${t2}-${t1})/(6*100):.2f}')"
# Expect: ~0.00
```

### Step 6 — relaunch autopilot

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 scripts/autopilot/autopilot.py start --tui
```

Watch for:
- `[INFRA_SKIP]` warnings — should be ZERO now (port plan fixed)
- `[host_health]` log entries — will fire on throughput-floor violations
- First few trials should show stable quality (not the 0.6-0.9 collapse from the previous bad run)

If autopilot still produces poor data within 30 trials, **kill it** and look at the per-trial reward attribution; this would suggest something other than the issues we addressed this session is contaminating.

### Step 7 — push the post-reboot progress + handoff updates

After Step 4 verdict is recorded:

```bash
cd /workspace
# Update handoffs/active/master-handoff-index.md item 19a with verdict
# Add progress/2026-05/2026-05-<date>.md with reboot test result
git add progress/ handoffs/active/master-handoff-index.md handoffs/active/reboot-validation-resume-2026-05-19.md  # this file
git commit -m "docs: 2026-05-<date> — post-reboot validation, host-throttle hypothesis <CONFIRMED|FALSIFIED>"
git push
```

---

## Items deferred until after this resume cycle

These were noted in `progress/2026-05/2026-05-16.md` and remain open:

1. **`cmd_stop --all` summary-print traceback** (separate from the `load_state` fix that landed). Does not block teardown but worth a follow-up; reproduce by running `stop --all` and looking for the traceback after the components-stopped table.
2. **`--compile-registry` default-on**. Currently opt-in. Switch to default after orchestrator/master port-plan reconciliation. Today's master fix was just for `architect_general` acceleration; the broader port-plan reconciliation (master 8080/81/82 vs orchestrator full-mode 8070/71/72) is the remaining blocker.
3. **Item 19 (AP-28-31 wire-ins)** — the AP-29/30/31 single-call wire-ins were scheduled for "next AR-3 restart". This reboot + autopilot relaunch IS that restart opportunity. Verify the wire-ins land or remain deferred.

---

## Quick reference — what changed in code (across the 4 repos)

| Repo | Commit | Key files |
|---|---|---|
| epyc-root | `ac2d899` | `progress/2026-05/2026-05-16.md` (new), `handoffs/active/autopilot-continuous-optimization.md` (+session 2026-05-16), `handoffs/active/master-handoff-index.md` (+item 19a), `wiki/speculative-decoding.md` (+2 new 2026-05-16 sections) |
| epyc-orchestrator | `a98c2e4` | `scripts/server/orchestrator_stack.py` (10+ edits — see commit body), `scripts/autopilot/host_health.py` (NEW), `scripts/autopilot/host_health_install.md` (NEW), `scripts/autopilot/safety_gate.py` (host-health wire-in), `src/registry/registry_validator.py` (NEW), `src/registry/registry_compiler.py` (NEW), `orchestration/model_registry.yaml` (port consolidation + slots + acceleration fix + MiniMax rename), `.gitignore` (+`.lean_cache_key`) |
| epyc-inference-research | `58dd9ac` | `orchestration/model_registry.yaml` (architect_general roles.X updated from stale Qwen3-235B to current Qwen3.5-122B, acceleration consolidated, server_mode.X acceleration block removed) |
| ik_llama.cpp | `e01e6443` (on `pr-1744`) | `examples/server/server-context.cpp` (omp.h include + slots_idle comment about failed pause_resource attempts + helper simplification) |

Pull requests / branch state:
- All main-branch commits are 1 ahead of upstream, 0 behind.
- `ik_llama.cpp` `pr-1744` branch needs `-u origin pr-1744` on first push (no upstream configured yet).

---

## If you want to skip the reboot for now

The stack is currently HEALTHY at 12.5 t/s frontdoor (and proportionally honest numbers for all roles). The autopilot CAN relaunch on this state — the registry validator, host_health, KMP_BLOCKTIME, `_NO_SPEC_DECODE`, and same-GGUF consolidation are all live. **You just won't recover the bench-era 26 t/s without the reboot test.** All of today's structural fixes are committed and (once pushed) durable across restarts.

The deferred items above can also be addressed independently of the reboot question.
