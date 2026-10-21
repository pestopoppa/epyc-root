# Claude sessions crash 2026-10-21 ~15:57Z -- forensics (read-only)

## Verdict
earlyoom (pid 3820) SIGTERM-killed the claude processes (plus firefox, codex, opencode, gnome-shell) in a ~20 s burst, 15:57:02-15:57:15Z. No API/429, tmux or container fault.

## Verified facts
- earlyoom cmdline: -M 41943040,20971520 (warn <40 GiB / kill <20 GiB MemAvailable) -s 100,100 -r 60 --sort-by-rss --ignore ^(llama-server|sd-server)$ --prefer ^llama-bench$ -N .../scripts/hooks/earlyoom_audit.sh. Started Oct 13 07:45:40; no other protection for claude/node/tmux.
- Hook log /workspace/logs/agent_audit-earlyoom.log (timestamps are +0200; 17:57 = 15:57Z) lists 12 kills, all 15:56:59Z-15:57:15Z:
  firefox x2, codex x4 (3213973, 1128294, 1201263, 3214394, 3213142), opencode 994916, gnome-shell 9637, python3 cite-check 3826820,
  **claude 3948550 (15:57:10Z), claude 721113 (15:57:12Z), claude 3944010 (15:57:15Z)**.
- Session jsonl last events match exactly: 3c4ca599 last 15:57:09.5Z, 9bcb2011 last 15:57:12.2Z, e3953395 (this one) last 15:57:13.4Z; next events only at resume 16:06:06-16:06:20Z (--resume procs started 16:06:04/14/19).
- Mem now: 1133 GB total, 580 used, 541 buff/cache, 17 free; PSI memory avg300 = 1.18 (some pressure occurred earlier). Cannot see the instant of the trigger (no memory sample at 15:57 on disk; fleet_watch/hygiene logs have no mem/swap lines).
- No Claude-side crash: ~/.claude has no debug/ or crash dumps; daemon.log shows only an unrelated idle daemon exit at 15:43.
- tmux was NOT restarted: `tmux ls` -> agent: 6 windows, created Oct 13 08:32:15. Host up 8d 8h; PID 1 is systemd (we see the host pid namespace), so no container/VS Code parent died. New tmux client via devcontainer exec at 14:47 is unrelated.
- Rate limit: 197 lines mentioning 429/"session limit" in this session's jsonl exist, but the last events before the gap are normal; a 429 kills a subagent, not the session. Not the cause.
- dmesg: Operation not permitted; journalctl not installed; /var/log has no kernel/syslog. Kernel OOM-killer evidence therefore unavailable (not needed: the earlyoom hook log is explicit).

## Survived and why (partly inference)
- llama-servers: matched by earlyoom --ignore regex (verified in cmdline).
- nohup'd launchers / earlyoom itself: small RSS; earlyoom picks by --sort-by-rss, and killed the largest non-ignored processes (claude node processes with large RSS, browsers, codex). Inference.
- Fourth session / driver_aba.log: only 3 claude kills are logged; the 4th window and the driver (ds41-w5 driver_aba.log is 0 bytes, last mtime 09:54) were not in the hook log. Inference: they died as children of killed claude/subagent shells (SIGHUP/pgroup teardown) -- unverified.
- Why the box was short: unverified, but consistent with two ~500 GB DS41 models in page cache plus parallel loads; MemAvailable must have fallen under 20 GiB (earlyoom kill threshold) transiently, likely from non-reclaimable (anon/mlock) allocations during parallel model loads.

## Prevention
1. Give earlyoom a protect list: add `--avoid '^(claude|node|tmux.*|codex|fish|zsh)$'` (deprioritise) -- or `--ignore` for claude/tmux if you accept earlyoom may then kill models/benches instead. Better: extend --prefer to `^(llama-bench|llama-cli|llama-perplexity|llama-quantize)$` so batch/measurement work is the victim, not sessions.
2. Lower the aggressiveness: current kill threshold 20 GiB with 541 GB cache is fine, but -r 60 report interval plus --sort-by-rss means first victims are the biggest RSS. Consider `--prefer` on the model-loader processes launching in parallel, and cap parallel loads (admission control on available memory: refuse to start a load when MemAvailable minus model size < 60 GiB).
3. Run claude sessions in a systemd scope/cgroup with `OOMScoreAdjust=-500` (or write -500 to /proc/<pid>/oom_score_adj; earlyoom honours oom_score_adj only via --avoid regex, so use regex).
4. Make critical drivers independent of session trees: launch with `systemd-run --user --scope`/`setsid nohup` and write logs outside the subagent shell; add pidfile + a resumable checkpoint.
5. Add a memory sample (MemAvailable, swap, PSI) every 30 s to a log so the next trigger is time-resolved; extend earlyoom_audit.sh to capture `free -m` and top RSS list at kill time.
