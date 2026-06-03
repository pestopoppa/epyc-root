# earlyoom — Userspace OOM Protection for the Multi-Model Box

**Status**: ready-to-deploy (pending `--dryrun` validation + operator install)
**Priority**: HIGH — lowest-hanging-fruit orchestration-robustness win (per user, 2026-06-03)
**Created**: 2026-06-03 (via research intake → deep-dive)
**Categories**: hardware_optimization, local_inference, inference_serving

## Objective

Deploy [earlyoom](https://github.com/rfjakob/earlyoom) as a userspace early-OOM daemon so that memory overcommit (concurrent/sequential multi-GB `--mlock` GGUF loads on the 1.1 TB box) results in a **single targeted process kill** instead of a **multi-minute kernel-OOM-killer freeze** of the entire host. It complements — does not replace — the preventive `max_mlock_gb`/`max_total_gb`/`reserve_kv_gb` ceilings in [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) and the mandatory sequential-load discipline.

## Why this is the lowest-hanging fruit

- **Deployable, not buildable**: mature (4.1k★, MIT, v1.9.0 2025-09-16, tests+CI), packaged in every major distro (`apt`/`dnf`), ~2 MiB RSS, self-`mlock`s so it stays responsive in the exact freeze window. Zero code to write, no fork.
- **High blast-radius mitigation**: the in-kernel OOM killer drops the entire page cache + empties buffers + swaps everything *before* killing — on a mlock'd box that is a seconds-to-minutes box-wide hang. earlyoom acts from userspace *before* that storm.
- **Directly protects the autopilot + nightshift**: runaway bench/eval processes become the first victims; the orchestrator control plane is hard-protected.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-659 | earlyoom — Early OOM Daemon | high | adopt_component |

Full deep-dive (mechanism, flag reference, victim-selection precedence, systemd-oomd/nohang comparison) → [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) **Part 5**.

## Decision: earlyoom over systemd-oomd / nohang

For **our** box specifically: systemd-oomd's primary trigger is swap-pressure (and we run a vestigial, essentially-unused 8 GB swap — see live facts), and its PSI/cgroup path needs a clean cgroup-v2 hierarchy with per-unit `MemoryAccounting` that our hand-launched `numactl … llama-server` processes don't have → coarse/ineffective targeting. earlyoom gives **per-process regex steering** + self-`mlock`. nohang adds a Python runtime + single-maintainer risk for marginal benefit. **Run exactly one OOM daemon** — systemd-oomd is currently `inactive/absent` (verified 2026-06-03), so no conflict to clear.

## Verified live facts (2026-06-03, read-only inventory)

These flip two assumptions from the initial intake read — **review carefully**:
- **NOT swapless**: there is an 8 GB `/swap.img` (PRIO -2, ~1.5 MB used). This matters: with earlyoom's default `-s 10`, the kill condition is *mem-below AND swap-below*, and free-swap stays ~100% → **earlyoom would never fire on memory pressure**. Fix: force `-s 100,100` (percent; both SIGTERM and SIGKILL swap-conditions ≈always-true) so **memory gates alone**. (The earlier `-S 100,100` in this stub was the *KiB* flag — wrong.) Cleaner long-term option: `swapoff /swap.img` + drop it from fstab (the 8 GB swap is pointless on a 1.1 TB mlock box) — validate earlyoom's zero-swap behavior separately before relying on it.
- **`oom_score` is nearly flat here**, so default (oom_score) victim selection is unpredictable: 133 GB model-server = `oom_score 742`; 730 MB embedder = `666`; 28 MB orchestrator = `666`. It could pick the control plane or an embedder as readily as a server. ⇒ **use `--sort-by-rss`** (deterministic RSS ranking) — *not* for the gameability reason (#344) the stub first gave, but because flat oom_score is unsafe here. A large runaway is then targeted by its size.
- **The control plane is NOT automatically safe under `--sort-by-rss`** (reviewer-caught correction): the orchestrator runs **`--workers 6`** → 1 master (`comm=python`, 28 MB) + **6 uvicorn workers (`comm=python`, ~1.09–1.26 GB each)**; autopilot is `comm=python`, 460 MB. With `--ignore` covering only `llama-server|sd-server`, the **6 workers are the 2nd–7th largest non-ignored processes** (after firefox @ 2 GB) → they are prime victims, not safe-by-smallness. Because their `comm=python` collides with a runaway python eval, a regex can't separate them. **The only thing that actually protects them is `oom_score_adj = -1000` (EXACTLY −1000)**: earlyoom's `is_larger()` skips any process with `oom_score_adj == -1000` in **both** the oom_score and `--sort-by-rss` paths (verified in upstream `kill.c`). `-900` does **NOT** protect (the earlier stub value was wrong). Setting −1000 on the control plane also cleanly **separates it from a runaway python eval** (which stays at 0 → killable). Caveat: −1000 makes them immune to the kernel OOM killer too, and a one-shot `choom` does **not** survive uvicorn worker respawn — the durable fix is `OOMScoreAdjust=-1000` in the orchestrator launcher/systemd unit.
- **Production servers vs benches ARE comm-distinguishable**: servers + embedders = `llama-server` (12 ch, no truncation); the only bench binary in this build is `llama-bench` (no `llama-cli`/`perplexity` built). `run_benchmark.py` runs as `python` (cover via `--sort-by-rss`). Managed image service = `sd-server` (16 GB).
- **Flags confirmed against the upstream MANPAGE**: `--sort-by-rss`, `--ignore` (hard, never-kill), `--avoid` (-300), `--prefer` (+300), `--dryrun`, `-N`, `-M`, `-s`, `-p`, `-r` all exist; all regexes match `comm` (15-byte). (`--ignore-root-user` does NOT exist — drop it.)

## Victim policy — the one real decision (review this)

Under `--sort-by-rss`, the largest RSS is *always* a production model-server (13–133 GB), so `--avoid` (only −300 oom_score, ≈−3 GiB-equiv) cannot protect them — only `--ignore` (hard) can. That forces a choice:

- **Policy A (recommended — protect production):** `--ignore '^(llama-server|sd-server)$'` **plus `oom_score_adj=-1000` on the control plane** (master + 6 workers + autopilot — REQUIRED, see live facts; `--ignore` alone does NOT cover the python control plane). earlyoom then culls the largest *remaining* non-protected process — a big `python` eval/runaway, a `llama-bench`, `firefox`, `docker`, an agent session (`claude`/`codex`) — and skips the model-servers + the −1000 control plane. **Trade-offs**: (1) without the −1000 step, the 6 uvicorn workers (~1.1–1.26 GB) are prime victims; (2) it can still kill a `claude`/`codex` agent session or firefox before a small runaway; (3) if an OOM is genuinely caused by model-server over-commit (rare — prevented upstream by the `max_mlock_gb`/`reserve_kv_gb` ceilings + sequential-load), earlyoom can't relieve it and may cascade through the non-protected innocents (#309). Right default because the realistic trigger is a *marginal non-model runaway* on top of the stable model baseline.
- **Policy B (relieve-pressure-fastest):** no `--ignore` on `llama-server` → earlyoom kills the biggest model-server (133 GB) to free memory fastest. Predictable + always relieves pressure, but takes down a production role mid-inference even when a smaller bench was the real culprit. Reserve for if model-server over-commit ever becomes the actual failure mode.

## Deployment plan (checklist) — Policy A

- [x] **Audited (2026-06-03)**: earlyoom NOT installed; systemd-oomd inactive/absent; 8 GB swap present; 445 GiB available / 688 GiB used at audit; comm names + RSS captured (above).
- [ ] **Verify installed-version flags**: `earlyoom --help` (or `man earlyoom`) confirms `--sort-by-rss` + `--ignore` exist in the *packaged* version (distro packages can lag master). If `--ignore` is absent, do NOT proceed with Policy A as written — fall back to Policy B or set model-server `oom_score_adj` instead.
- [ ] **Re-verify protected comm names at deploy time** (truncated to 15 bytes; **bash**): `for p in $(pgrep -x llama-server); do cat /proc/$p/comm; done` and likewise for the orchestrator/autopilot — process names can change across restarts. (Run under bash, e.g. `bash -c '...'`, if your interactive shell is fish.)
- [ ] **Install**: `sudo apt install earlyoom` (or `dnf`/EPEL) — provides the hardened systemd unit + `/etc/default/earlyoom`.
- [ ] **Configure** `/etc/default/earlyoom`:
  ```
  EARLYOOM_ARGS="-M 41943040,20971520 -s 100,100 -r 60 -p --sort-by-rss \
  --ignore '^(llama-server|sd-server)$' \
  --prefer '^llama-bench$' \
  -N /mnt/raid0/llm/epyc-root/scripts/hooks/earlyoom_audit.sh"
  ```
  - `-M 41943040,20971520` = **absolute** 40 GiB SIGTERM / 20 GiB SIGKILL (NEVER percent at 1.1 TB — 10% fires with 110 GB free). With 445 GiB currently available this won't false-fire; raise SIGTERM (e.g. 64 GiB) for more reaction time if a single load can spike >40 GiB of *committed* (non-reclaimable) memory.
  - `-s 100,100` = **percent** (lowercase). Neutralizes the swap gate so memory alone triggers both SIGTERM and SIGKILL (see live facts).
  - `--sort-by-rss` — deterministic RSS ranking (flat oom_score here makes default mode unsafe).
  - `--ignore '^(llama-server|sd-server)$'` — hard-protect production model-servers + embedders + the managed image service.
  - `--prefer '^llama-bench$'` — bias toward culling a runaway manual benchmark first.
- [ ] **Protect the control plane — REQUIRED, not optional** (this is the load-bearing protection under `--sort-by-rss`; verified earlyoom skips `oom_score_adj==-1000` in both modes). `choom` takes a **single** `-p PID`, so loop (**bash**):
  ```bash
  master=$(pgrep -f 'uvicorn src.api' | head -1)
  for pid in "$master" $(pgrep -P "$master") $(pgrep -f 'autopilot.py start'); do
    [ -n "$pid" ] && sudo choom -n -1000 -p "$pid"
  done
  ```
  Use exactly **−1000** (−900 does not protect). A one-shot `choom` does **not** survive uvicorn worker respawn — wire `OOMScoreAdjust=-1000` into the orchestrator launcher / systemd unit for durability.
- [x] **`-N` audit hook written + tested**: `scripts/hooks/earlyoom_audit.sh` — fork-free (bash parameter-expansion + builtins), JSON-escapes **every** field incl. `EARLYOOM_NAME` (the manpage warns it may contain newlines/control chars; maps all C0 control chars → space under `LC_ALL=C`). Emits exactly one valid JSON-lines `EARLYOOM_KILL` record per kill (re-verified with a newline in NAME + control chars in all fields → `json.loads` passes). Off-by-default sentinel-write for a future pause-loads watcher.
- [ ] **VALIDATE in `--dryrun -d` FIRST** (extended window), against a live full stack: `earlyoom --dryrun -d -M 41943040,20971520 -s 100,100 --sort-by-rss --ignore '^(llama-server|sd-server)$' --prefer '^llama-bench$' -r 5`. Confirm the would-kill candidate is always a non-protected runaway, **never** the orchestrator/autopilot/a model-server. Optionally drive a `stress-ng --vm` ramp in a quiet window and confirm it selects the stressor.
- [ ] **Arm**: `sudo systemctl enable --now earlyoom`; `systemctl status earlyoom`; confirm a periodic report line appears.

## Open Questions

- **Steady-state headroom**: does our normal peak resident set ever legitimately approach 40 GiB-free? If so the SIGTERM threshold needs raising or model loads need a memory precheck to avoid false kills mid-load.
- **Post-kill cascade (issue #309)**: there is **no built-in post-kill backoff**, and mlock'd pages free slowly → earlyoom can kill several procs in ~100 ms succession before headroom is reflected. Mitigation: set KILL far enough below SIGTERM that a single kill restores headroom past the SIGKILL line, and have the `-N` hook (or autopilot) **pause new model loads immediately after any kill**. Is a pause-loads hook worth wiring into `orchestrator_stack.py`?
- **Pre-kill hook (`-P`)**: worth firing the autopilot host-health remediation (drop_caches/throttle-check) *before* a kill? Risk: a pre-kill script that itself allocates under pressure is dangerous — keep allocation-free if used.

## Notes

- Maturity/credibility: high. Single primary maintainer (rfjakob) but long track record, broad distro adoption (was Fedora 32 default), real test/CI ratio, tiny attack surface.
- This is an **operator action** (privileged `apt install` + `systemctl`). Prepare the exact commands; the user runs the install (suggest `! sudo apt install earlyoom` in-session).
- Cross-refs: [`single-instance-system-tuning.md`](single-instance-system-tuning.md) (deep-dive correction section), [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (preventive ceilings), `feedback_autopilot_host_health_remediation`, `feedback_use_orchestrator_stack_for_lifecycle`.
