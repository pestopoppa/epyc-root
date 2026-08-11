# Agent Session Control Surface

**Status:** recommendation, nothing implemented
**Date:** 2026-07-29
**Author:** investigation session (read-only w.r.t. `tmux_adapter.py`)
**Owning handoff:** `handoffs/active/session-bus-thin-dispatcher.md` (M5 adapter)

---

## 0. TL;DR

**There is a first-class, non-TTY control surface for Codex CLI, and it does everything we
need.** `codex app-server` is a JSON-RPC-over-WebSocket server with 90 request methods. A TUI
launched with `codex --remote unix://<sock>` becomes a *client* of that server, and any other
client on the same socket can:

* enumerate live sessions (`thread/loaded/list`),
* read a session's **runtime-reported** busy/idle state (`thread/read` → `thread.status`),
* subscribe to push transitions (`thread/status/changed`, `turn/started`, `turn/completed`),
* **inject a message into a running session** (`turn/start`), and
* **inject a message into a session that is mid-generation** (`turn/steer`).

All five were measured working end-to-end today against a real authenticated Codex TUI in a
disposable tmux window. This eliminates, at once: paste-blob thresholds, chunking, Enter
verification, composer-mode prefixes, and — most importantly — **the heartbeat deadlock**, because
the busy/idle signal comes from the runtime rather than from the agent that is stuck.

Claude Code has **no equivalent injection surface**, but it does have a documented non-TTY
*status* surface (`claude agents --json`) that solves the same deadlock for the observation half.

The three structural hypotheses for the 15-second `send-keys` timeout were each **falsified under
measurement**; the failure was not reproduced. `tmux load-buffer`+`paste-buffer` is **not** a
workaround for the paste blob — measured, it blobs and truncates identically.

**Recommendation: Option A (Codex on `app-server`) + Option D (Claude on `agents --json`).**

---

## 1. Environment under test

| Component | Version / value | How obtained |
|---|---|---|
| Codex CLI | `codex-cli 0.146.0` | `codex --version` |
| Codex install | npm, `/usr/local/share/npm-global/lib/node_modules/@openai/codex` | `package.json` |
| Codex real binary | `.../node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex` | `pgrep -af` |
| Claude Code | `2.1.220 (Claude Code)` | `claude --version` |
| Claude install | native single binary, `/home/node/.local/share/claude/versions/2.1.220` | `readlink -f $(which claude)` |
| tmux | `3.5a` | `tmux -V` |
| `CODEX_HOME` (live) | `/home/node/.codex` | env |
| Host load during tmux timing | `load average: 96.69` | `uptime` |

All experiments ran in disposable tmux sessions (`ctlprobe1`, `ctlsk`, `ctlsk2`, `ctlsk9`) created
and destroyed by this session, plus an isolated `CODEX_HOME` at
`/mnt/raid0/llm/tmp/agent-ctl-probe/home`. **The live `agent` session was never written to** — it
was read with `list-sessions` / `list-windows` only, and held 9 windows before and after
(`coordinator htop btop inference mainA auditor mainB mainC mainD`).

The isolated `CODEX_HOME` needed a credential to authenticate. It was **symlinked**, not copied,
to `/home/node/.codex/auth.json`, and the symlink was **removed at the end of the
investigation** (verified absent). No credential was copied to rest.

---

## 2. Question 1 — Does Codex CLI have a non-TTY control surface?

### 2.1 Yes. `codex app-server`.

`codex --help` exposes, among others:

```
  exec            Run Codex non-interactively [aliases: e]
  mcp-server      Start Codex as an MCP server (stdio)
  app-server      [experimental] Run the app server or related tooling
  remote-control  [experimental] Manage the app-server daemon with remote control enabled
```

and on the top-level interactive command:

```
      --remote <ADDR>
          Connect the TUI to a remote app server endpoint.
          Accepted forms: `ws://host:port`, `wss://host:port`, `unix://`, or `unix://PATH`.
```

`codex app-server --help`:

```
      --listen <URL>
          Transport endpoint URL. Supported values: `stdio://` (default), `unix://`,
          `unix://PATH`, `ws://IP:PORT`, `off`   [default: stdio://]
```

The protocol is self-documenting. **Measured**:

```bash
codex app-server generate-json-schema --out <DIR>
```

emits 37 top-level schema files plus `v1/` and `v2/` directories (≈1.1 MB of JSON Schema),
including `codex_app_server_protocol.v2.schemas.json`. Extracting the `method` enums:

* **90 client request methods** (`ClientRequest.json`)
* **70 server notification methods** (`ServerNotification.json`)

The methods that matter here:

| Method | Kind | What it gives us |
|---|---|---|
| `thread/loaded/list` | request | thread ids of sessions **currently loaded in memory** |
| `thread/read` | request | full thread incl. `thread.status` (runtime-reported) |
| `turn/start` | request | **send a message to a session**, no keystrokes |
| `turn/steer` | request | **send a message to a session that is mid-turn** |
| `turn/interrupt` | request | cancel the running turn |
| `thread/inject_items` | request | insert items into the transcript |
| `thread/status/changed` | notification | **push** idle/active transitions |
| `turn/started` / `turn/completed` | notification | push turn boundaries |
| `thread/goal/set` / `get` / `clear` | request | structured per-thread objective |
| `item/agentMessage/delta`, `item/reasoning/textDelta` | notification | live token stream |

`ThreadStatus` is a tagged union with variants `notLoaded`, `idle`, and `active` (the `active`
variant carries `activeFlags`, drawn from `waitingOnApproval` / `waitingOnUserInput`).

### 2.2 Transport: `unix://` speaks **WebSocket**, not raw line-JSON

This is a non-obvious detail that cost two failed attempts and is worth recording.

**Measured.** Connecting an `AF_UNIX` socket and writing newline-delimited JSON-RPC caused the
server to close the connection immediately (`BrokenPipeError`), with nothing in the server log.
The `--remote` help text lists `ws://` and `unix://` as interchangeable forms, which is the clue:
the unix transport carries **RFC 6455 WebSocket framing**. A hand-written minimal WS client
(HTTP `Upgrade` over `AF_UNIX`, masked text frames) handshook successfully:

```
HTTP/1.1 101 Switching Protocols
connection: Upgrade
upgrade: websocket
sec-websocket-accept: l/0354gLS0r13RZFOi16VGGwpOk=
```

Second detail: the request envelope is `{"id", "method", "params"}` with **no `jsonrpc` field**,
and `params` is **required** on every request (from `ClientRequest.json`: `"required": ["id",
"method", "params"]`). Sending `"jsonrpc": "2.0"` is what caused the initial disconnects.

`initialize` then returns:

```json
{"id": 1, "result": {"userAgent": "probe/0.146.0 (Ubuntu 25.10.0; x86_64) VTE_7600_ (probe; 0.1)",
 "codexHome": "/mnt/raid0/llm/tmp/agent-ctl-probe/home",
 "platformFamily": "unix", "platformOs": "linux"}}
```

### 2.3 The decisive experiment — external client drives a live TUI

**Setup (measured, reproducible):**

```bash
P=/mnt/raid0/llm/tmp/agent-ctl-probe
CODEX_HOME=$P/home codex app-server --listen "unix://$P/as.sock" &          # headless server
tmux new-session -d -s ctlprobe1 -n rtui \
  "cd $P && CODEX_HOME=$P/home codex --remote unix://$P/as.sock"            # TUI as a client
```

**Result 1 — the TUI's session is visible to an unrelated client.** From a *separate* WS
connection that never touched the tmux pane:

```
thread/loaded/list -> {"data": ["019faea2-ad08-7a02-9e64-d6c11da017ec"], "nextCursor": null}
```

**Result 2 — an external client can read authoritative busy/idle state.**

```
thread/read {"threadId": "019faea2-..."} -> thread.status = {"type": "idle"}
```

**Result 3 — an external client can send the session a message.** `turn/start` with
`input: [{"type":"text","text":"Reply with exactly the single word PONG and nothing else."}]`
returned in **0.1 s**, and the tmux pane rendered:

```
› Reply with exactly the single word PONG and nothing else.

• PONG
```

with push notifications on the observing connection:

```
(0.1s) thread/status/changed {"status": {"type": "active", "activeFlags": []}}
(6.4s) thread/status/changed {"status": {"type": "idle"}}
```

**Result 4 — an external client can interrupt and redirect a session that is mid-generation.**
A long turn was started ("Count slowly from 1 to 40…"), and 6.5 s in, while the model was
streaming, `turn/steer` was issued with the turn id from the `turn/start` response:

```
turn/steer {"threadId": "...", "expectedTurnId": "019faea4-a769-7810-8282-9c48b000aa96",
            "input": [{"type":"text","text":"STOP counting. Instead reply with exactly: STEERED"}]}
  -> {"result": {"turnId": "019faea4-a769-7810-8282-9c48b000aa96"}}
```

Pane afterwards:

```
  40 — Forty completes the count.

› STOP counting. Instead reply with exactly: STEERED

• STEERED
```

`expectedTurnId` is an optimistic-concurrency precondition — verbatim from `TurnSteerParams.json`:
*"Required active turn id precondition. The request fails when it does not match the currently
active turn."* That is exactly the guard `tmux_adapter.py` builds by hand out of composer
inspection, except the server enforces it atomically and cannot be fooled by a repaint frame.

**This is the whole answer to the assignment.** Every failure mode in the brief — paste blobs,
1024-char truncation, chunk gaps, Enter swallowing, composer-mode prefixes, `@`-pickers,
cursor-anchored verification — is an artifact of pretending to be a keyboard. None of it exists
on this path. `turn/start` returns a request id or an error; there is nothing to verify by
screen-scraping.

### 2.4 What is *not* available on this install

**Measured constraint.** The *managed daemon* subcommands refuse:

```
$ codex app-server daemon start
Error: managed standalone Codex install not found at $CODEX_HOME/packages/standalone/current/codex
This command requires the standalone install managed by the Codex installer, because the daemon
starts and updates app-server from that fixed path.
```

`/home/node/.codex/packages` does not exist — we installed via npm. So `codex app-server daemon
{start,restart,stop,bootstrap}` and `codex remote-control {start,stop,pair}` are unavailable
**unless** we switch to the standalone installer (`curl -fsSL https://chatgpt.com/codex/install.sh
| sh`).

This does **not** block the recommendation: `codex app-server --listen unix://PATH` runs the
server directly in the foreground and needs none of that. We supervise it ourselves, which we
prefer anyway (it becomes a normal `orchestrator_stack.py`-style managed service rather than a
vendor-managed daemon that self-updates on a fixed path).

Also noted: `codex remote-control` is aimed at pairing with OpenAI's cloud/app, not at local
control. `features list` shows `remote_control  removed  false`. Not our path.

### 2.5 Claude Code — the honest asymmetry

**Measured**, by me, using documented surfaces only:

* `claude agents --json` works with no TTY and returns per-session state:

```json
[ { "id": "c65dd6f5", "kind": "background", "name": "Fable5-Review", "state": "blocked" },
  { "pid": 12493, "kind": "interactive", "sessionId": "a06c777b-…", "name": "workspace-13",
    "status": "busy" },
  { "pid": 21771, "kind": "interactive", "sessionId": "484e6d12-…", "status": "busy" },
  { "pid": 96028, "kind": "interactive", "sessionId": "27a372c8-…", "status": "busy" } ]
```

* The backing files are `~/.claude/sessions/<pid>.json`, one per live interactive session:

```json
{"pid":21771,"sessionId":"484e6d12-…","cwd":"/workspace","startedAt":1785335292914,
 "version":"2.1.220","peerProtocol":1,"kind":"interactive","entrypoint":"cli",
 "name":"workspace-ba","status":"busy","updatedAt":1785341803484,"statusUpdatedAt":1785341803484}
```

* Headless/streaming flags confirmed present in `claude --help`: `-p/--print`, `--output-format`
  (`text|json|stream-json`), `--input-format` (`text|stream-json`), `--session-id`, `--resume`,
  `--continue`, `--fork-session`, `--replay-user-messages`, `--include-partial-messages`,
  `--include-hook-events`, `--bg/--background`, `--agents <json>`, `--mcp-config`, `--bare`.

**But**: `-p --input-format stream-json` is a *new* session that the caller owns over stdin/stdout.
It does not attach to an already-running interactive session. There is **no measured Claude Code
equivalent of `turn/start` against a live TUI**.

> **Caveat on `status`.** All three interactive sessions reported `busy` simultaneously, and at
> least two of them were sitting at their `❯` prompt with subagents running. So `status` is
> **process-level** ("this process has work in flight, including subagents"), not composer-level
> ("the operator cannot type right now"). It is strictly better than the self-reported heartbeat —
> the runtime writes it, so a stuck agent cannot make it lie in the *stale* direction — but it is
> conservative, and a session with long-running subagents will read `busy` while its composer is
> perfectly free. Validate the `idle` transition before gating on it.
>
> Also measured: `~/.claude/sessions/12493.json` had mtime `15:39` while still reporting `busy` at
> `16:08`. The file is written **on state transition, not on a heartbeat**, so *file mtime is not a
> liveness signal* — read the `status` and `statusUpdatedAt` fields and pair them with a
> `/proc/<pid>` existence check. A crashed session leaves a stale `busy` file behind.

**A parallel investigation into Claude Code's internals was flagged by the harness for credential
exploration** (it read the background-agent daemon's `control.key` and a roster file containing
plaintext socket auth tokens, and reverse-engineered the shipped binary). Those findings are
deliberately **excluded** from this document and from the recommendation. This section rests only
on `--help` output, `agents --json`, and world-readable session files that I re-derived myself.
See §7.

---

## 3. Question 2 — Why did `send-keys -l` time out on one pane?

**Not reproduced. Three structural hypotheses tested; all three falsified.**

### H1 — pty input backpressure (the pane stopped reading stdin) — **FALSIFIED**

If the target process stops reading its pty, the kernel's N_TTY input buffer (4096 B) fills and
further writes block. Tested against `tmux new-window "exec sleep 3600"` — `exec` matters, or the
login shell reads stdin and the condition never arises. (First attempt did exactly that: the pane
showed `pane_current_command=fish`, which is *also* an independent confirmation of the adapter
header's note that `pane_current_command` is uninformative.)

With a genuine non-reading pane process (`cmd=sleep`, pid confirmed):

```
cumulative=  400 +400 ->   0.00s rc=0
cumulative=  800 +400 ->   0.00s rc=0
...
cumulative= 6400 +400 ->   0.00s rc=0        (16 consecutive sends, none blocked)
```

And against `exec cat > /dev/null`: 1000, 4000, 8000, 16000 chars — all `0.00s`, 29,000 chars
cumulative. **tmux 3.5a buffers pane input in userspace (libevent) and returns immediately.** It
does not apply pty backpressure to `send-keys`.

### H2 — a stuck attached client blocks the single-threaded tmux server — **FALSIFIED**

The live `agent` session has `session_attached=2`. tmux's server is single-threaded, so a client
whose terminal stops draining is a plausible global stall. Tested: disposable session with a
window spamming `od -c` of `/dev/urandom`, a real attached client on its own pty via `script`,
then `SIGSTOP` on that client and 10 s for output to back up.

```
--- A. healthy attached client ---
   send-keys -l -> ctlsk9:quiet: (0.0, 0)
   send-keys -l -> ctlsk9:spam:  (0.0, 0)
   list-windows                : (0.0, 0)
--- B. client SIGSTOPped (stuck terminal); 10s for output to back up ---
   send-keys -l -> ctlsk9:quiet: (0.0, 0)
   send-keys -l -> ctlsk9:spam:  (0.0, 0)
   list-windows                : (0.0, 0)
   display-message             : (0.0, 0)
   load+paste-buffer           : (0.01, 0)
```

tmux uses non-blocking writes to client sockets. A frozen client does not stall the server.

### H3 — fork/exec latency on a saturated host — **FALSIFIED (at time of measurement)**

The adapter wraps every tmux call in `subprocess.run(..., timeout=15)`, and a 12 kB nudge becomes
~30 separate `tmux` process spawns. On a box running a decision-grade measurement this looked
promising. Measured at `load average: 96.69` (96 cores, fully saturated):

```
/bin/true (bare fork+exec) : n=150 min=0.3ms med=0.3 p90=0.5 p99=1.1 max=1.4
tmux display-message       : n=150 min=1.4ms med=1.8 p90=2.5 p99=3.7 max=3.9
tmux send-keys -l (400ch)  : n=50  min=1.5ms med=1.6 p90=1.8 p99=2.1 max=2.1
```

No fat tail. Four orders of magnitude away from 15 s.

### What remains

The 15 s figure is exactly `_tmux()`'s own `subprocess.run(timeout=15)`, so the *timer* is ours —
but I could not make tmux take anywhere near that long under any condition I could construct.

The "**truncated at the same ~380-char point, twice**" detail is the most informative surviving
clue, and it has a mundane reading that fits everything: `NUDGE_CHUNK_CHARS = 400`. If chunk 1
(400 chars) was delivered and the `tmux` invocation for chunk 2 was what hung, the composer would
hold ~400 chars of pending text — which is what was seen, and which is precisely the state
`_send_message_chunked()` warns about (*"WARNING: {start} chars were already typed … and are still
pending in that composer"*). Under that reading the truncation point is a **chunk boundary, not a
buffer limit**, and it is reproducible-by-construction rather than mysterious.

**Recommended diagnostic** (cheap, and it costs nothing to add): when a `_tmux()` call exceeds ~2 s,
log the full argv, the elapsed time, and `#{session_attached} #{pane_in_mode} #{pane_pipe}
#{window_flags} #{client_activity}` for the target. One capture of a live occurrence would settle
this. I am explicitly **not** claiming the cause is known.

**Under the Option A recommendation this question becomes moot** — there are no keystrokes to
time out.

### `load-buffer` + `paste-buffer` is NOT a workaround — **measured negative**

The brief names this as the obvious alternative. It is not one, for the blob problem.

Measured against a real Codex CLI 0.146.0 TUI, a 1991-char message via `tmux load-buffer` +
`tmux paste-buffer` **without** `-p` (i.e. no bracketed-paste markers):

```
paste-buffer (no -p): 0.002s rc=0
› [Pasted Content 1024 chars]
BLOB MARKER PRESENT: True
ALPHA visible: False | OMEGA visible: False
full text landed (whitespace-insensitive): False
```

Identical failure to `send-keys -l`: blobbed, and **truncated at 1024 chars** — both the leading
`ALPHA` and trailing `OMEGA` sentinels were lost. Codex detects a paste from the *input burst*,
not from bracketed-paste markers, so suppressing the markers changes nothing.

This **confirms and does not contradict** the adapter's 2026-07-28 calibration block: sub-threshold
chunking with a real inter-chunk gap remains the only working keystroke-based delivery. It also
adds a new fact to it — `paste-buffer` is not an escape hatch, so nobody should try it again.

*(Note: the adapter header records the Codex blob threshold at 1001 chars for v0.145.0. The 1024-char
truncation cap is re-confirmed here on v0.146.0. The 1001-char onset threshold was not re-bisected
on 0.146.0 and should not be assumed to have carried over unchanged.)*

---

## 4. Question 3 — A better liveness signal than the self-reported heartbeat

The deadlock, restated: the heartbeat is written by the agent, so an agent that has stopped cannot
say so, and `probe()` refuses every nudge on `state == "working"`. The fix is a signal written by
**something other than the agent**.

Ranked by reliability, and by the property that actually matters — can it separate *thinking
silently* from *waiting at a prompt*?

| # | Signal | Separates thinking/waiting? | Written by | Verdict |
|---|---|---|---|---|
| 1 | **Codex `thread/read` → `thread.status`** and `thread/status/changed` | **Yes, exactly** (`idle` / `active` + `activeFlags`) | the Codex runtime | **Use.** Measured. Push *and* poll. Cannot go stale — it is state, not a timestamp. |
| 2 | **Codex rollout terminal record** — last record in `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-*.jsonl` is `event_msg/task_complete` or `turn_aborted` ⟹ idle | **Yes** | the Codex runtime | **Use as the no-app-server fallback.** 64/64 correct on today's rollouts plus one live transition. Requires pid→rollout mapping via `/proc/<pid>/fd` and filtering `thread_source=='user'` (subagents get their own rollout file with the same `session_id`). |
| 3 | **Claude `claude agents --json` / `~/.claude/sessions/<pid>.json` `status`** | **Partially** — process-level, counts subagents as busy (§2.5) | the Claude runtime | **Use for Claude.** Strictly better than the heartbeat; conservative in the safe direction. |
| 4 | **tmux `pane_title` braille spinner** (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` prefix) | Yes, for **Codex only** | Codex TUI, via terminal title | **Cheap prefilter.** One `tmux list-panes -F '#{pane_title}'`, single sample, no `/proc`. Agreed with signal #2 in every sample observed. **Does not work for Claude Code** — Claude's title char was a *static* `⠐` on a window that `capture-pane` showed as `Imagining… (9m 30s)`. Unverified during long blocking tool calls. |
| 5 | **Process CPU delta over ≥20 s** from `/proc/<pid>/stat` | Yes for Codex; **no** for Claude | kernel | **Corroborator only.** Codex generating 3.1–6.1 % mean vs idle 0.23–0.27 % (~12–26× separation), but per-3 s ticks overlap (busy dips to 0.7 %), so a ≥20 s window is required. **Invalid for Claude Code**: pid 21771 burned 17 % CPU and read 18.5 GB in 20 s while its main thread sat at the prompt, because subagents run in-process. |
| 6 | Rollout-file mtime staleness | Weakly | runtime | **Do not gate on it.** Median inter-record gap 0.67–0.92 s but p99 ≈ 14–19 s and max 74–80 s *within a turn*; the same files show 575–665 s gaps that are genuinely idle. Any safe threshold exceeds 90 s and still conflates "idle" with "slow tool call". |
| 7 | `/proc/<pid>/io` `wchar` delta | Yes, noisily | kernel | Idle 24–62 KB/30 s vs busy 0.4–27 MB/30 s. Worst case only ~7× separation. Weaker than #5. |
| 8 | `history.jsonl` last ts per `session_id` | Turn *starts* only | runtime | **Complement.** `last_history_ts > last_task_complete_ts` ⟹ turn in flight. Frozen 8 min while four sessions generated — useless alone. |
| 9 | `window_activity` / `pane_last_activity` | No | tmux | Already known bad (adapter header). `pane_last_activity` empty on 3.5a; `window_activity` only tracks output while attached. |
| 10 | `pane_current_command` | No | tmux | Reads `fish`/`node` regardless — **independently re-confirmed** in this session's H1 experiment. |
| 11 | SQLite `-wal` mtime/size under `CODEX_HOME` | No | shared | **Unusable.** `state_5.sqlite`, `logs_2.sqlite` are opened by *every* codex process; no per-session attribution. |
| 12 | ESTABLISHED TCP to the model endpoint | **No — disproven** | kernel | An **idle** codex TUI holds the *same* 2–3 keep-alive connections to `172.64.155.209:443` as a busy one, with empty queues in every sample. Do not use. |
| 13 | Thread count (`/proc/<pid>/status Threads:`) | No | kernel | 202–207 for every codex TUI regardless of state. Zero signal. |
| 14 | `/home/node/.codex/log/` | — | — | Empty directory, mtime 2026-05-27. Nothing there. |

**MEASURED CORRECTIONS to signal #2, appended 2026-07-29 by `auditor` while implementing C36.**
The claim's substance holds and is in fact *stronger* than stated, but four details would have
produced a wrong implementation and one of them is exploitable on a live pid right now:

* **"64/64 correct on today's rollouts" conflates two things.** 60 of today's 64 files end in a
  terminal record; the other 4 are the 4 live TUIs mid-turn, i.e. the signal correctly reporting
  *busy*. Defensible as a classification claim, false as "64 files ended terminal". **Cite the
  corpus instead: 400 files sampled at random from the full 4,233 gave 385 `task_complete` +
  15 `turn_aborted` = 400/400.** The doc undersells its own evidence.
* **n is 7, not 64.** 57 of today's 64 rollouts are *subagent* files. The population the signal
  actually serves — user sessions you might nudge — had n=7 today.
* **`thread_source == 'user'` is UNSAFE as written.** 8 corpus files (April–May, older
  `cli_version`) carry **no `thread_source` field at all**; a literal equality test misclassifies
  them as non-user. Use `!= 'subagent'`, or fail closed on absence.
* **The parent holds *finished* subagent fds open.** Measured 16:38 UTC on pid 257808: fd 39 →
  a subagent rollout reading `task_complete`, fd 45 → its own user rollout reading
  `custom_tool_call`. Picking the wrong fd yields "idle" for an agent that is **mid-tool-call**.
  The `thread_source` filter is not hygiene, it is load-bearing, and the unsafe reading is
  available on a live pid today.
* Two more, minor: a session's subagent files can sit in a date directory containing **no** parent
  user file (a 31-file group today), so never resolve the parent by scanning a date dir — go
  through the fd. And only the musl `codex` binary holds rollout fds; `node` wrappers and
  `codex-code-mode-host` hold none.

*Robustness, measured:* `tail -n 1` is size-independent (~10 ms; sub-ms in-process) and 1,800 reads
against actively-appended files produced **0** parse failures — but the longest record today is
192 KB, well past any single-write atomicity guarantee, so a torn tail cannot be *proven*
impossible. Treat "last line does not parse" as an expected transient: retry once, then report
unknown and fail closed. *Supporting property, and it is the one the signal depends on:*
`task_complete` is a **stable resting tail** — across all of today's files the record following a
`task_complete` is only ever `task_started` or `thread_settings_applied`, never the frequent
mid-turn `token_count`.

**The key structural point:** signals #1–#3 are *state*, not *timestamps*. The current heartbeat
fails in two ways — it can say `working` when the agent is dead, and it can be *stale* while the
agent is healthy (the 2026-07-27 incident recorded in `CLAUDE.md`). A runtime-reported status has
neither failure mode, because nothing is being asserted about freshness: `thread/read` answers
"what is this thread doing **now**".

**Direction of error.** The adapter is correctly fail-closed, and that must not be weakened. Note
which way each replacement errs: Codex `thread.status` is exact; Claude `status` over-reports busy
(refuses a nudge that would have been fine — recoverable). Neither errs permissive. That is the
property to preserve in any implementation.

---

## 5. Question 4 — Startup robustness

The failure: a freshly spawned Codex pane died instantly and silently because the CLI presented an
update prompt at startup; `cmd_spawn` reported success because `new-window` exited 0.

Four mitigations, complementary rather than alternative:

1. **Suppress the update prompt at the source.** `codex features list` shows `in_app_updates
   stable true`. **Measured**: both `codex --disable in_app_updates …` and `codex -c
   'features.in_app_updates=false' …` are accepted by the CLI. The config form can be pinned once
   in `$CODEX_HOME/config.toml` so it applies to every launch, including ones nobody remembered to
   flag. *(Flag acceptance measured; suppression of the prompt itself is inferred — it could not
   be observed because no update was pending: `version.json` reads
   `{"latest_version":"0.146.0","last_checked_at":"2026-07-29T14:19:16Z","dismissed_version":null}`.)*

2. **Pin the CLI version.** The npm install makes this trivial and it removes the entire class:
   `npm install -g @openai/codex@0.146.0`, with upgrades performed deliberately at a seam. This
   also protects the calibration constants in `tmux_adapter.py`, which are version-specific — the
   blob thresholds were measured on 0.145.0 and the CLI silently moved to 0.146.0 today.

3. **Pre-flight before spawn.** Compare `codex --version` against a pinned expectation, and check
   `version.json` for a pending `latest_version != dismissed_version`, before creating the window.
   Cheap, and it converts a silent death into a refusal with a reason.

4. **Post-spawn liveness verification (C30b) — already implemented.** `SPAWN_SETTLE_S = 2.0` plus
   a `list-windows` re-check now catches the death. Keep it: it is the backstop for the classes
   (1)–(3) do not anticipate.

**Under Option A, (1)–(4) all get much less load-bearing**, because the thing being spawned for
control purposes is `codex app-server` — a headless process with no TUI, no update modal, and a
socket whose existence is a positive, checkable readiness signal. "Did it start?" becomes "does
`initialize` return?" rather than "is the window still there 2 s later?".

Independently: the `--remote` TUI *also* fails safely. When I launched one against an
unauthenticated `CODEX_HOME`, the pane did not die — it rendered a sign-in chooser and stayed
alive, i.e. it degrades to a visible blocked state rather than a vanished window.

*(An incidental finding worth recording: launching a TUI as `codex … | tee log` kills it instantly
and silently — stdout is not a tty. That is a second, independent instance of the "spawn reported
success, window is gone" class, and it is entirely in our control. Never pipe a TUI launch.)*

---

## 6. Options, ranked

### Option A — Codex mains on `app-server`; adapter talks JSON-RPC (**recommended**)

Run one `codex app-server --listen unix://<path>` as a managed service. Launch each Codex main as
`codex --remote unix://<path>` inside its tmux window, exactly as today — the operator keeps a
visible, attachable, scrollable pane. The adapter gains a Codex transport that resolves an agent id
to a thread id and calls `thread/read` / `turn/start` / `turn/steer`.

* **Cost:** a supervised service; a ~200-line WS+JSON-RPC client (the framing is done — the probe
  client written today is ~90 lines and works); an agent-id → thread-id mapping; roster/config
  changes to record the socket path.
* **Risk:** `app-server` is marked `[experimental]`, so the protocol can move between CLI versions
  — which makes version pinning (§5.2) a hard prerequisite, not a nicety. Single point of failure:
  if the app-server dies, every Codex main attached to it is affected. One socket shared by all
  mains means one blast radius; a socket per main is the conservative variant and costs only
  process count.
* **What must change:** `tmux_adapter.py` grows a second transport, and `probe()` grows a
  `thread.status` source that outranks the heartbeat for Codex agents. `send-keys` stays for
  Claude mains. Two other agents are editing this file right now — sequencing is a coordination
  question, not a technical one.
* **What it buys:** removes chunking, blob thresholds, Enter verification, composer-mode prefix
  refusals, `@`-picker refusals, cursor-anchored composer inspection, *and* the heartbeat
  deadlock — for Codex. Plus a capability we do not have at all today: **safely messaging a busy
  session** via `turn/steer`, which makes the whole "wait for idle" dance optional rather than
  mandatory.

### Option B — Keep `send-keys`, replace only the liveness guard (**recommended as the immediate step**)

Leave delivery exactly as calibrated. Replace *"the heartbeat does not say working"* with a
runtime-reported source: Codex rollout terminal record (§4 #2) or `pane_title` spinner (§4 #4),
Claude `agents --json` (§4 #3), with the heartbeat demoted to a corroborator.

* **Cost:** small and self-contained. No new services, no new protocol.
* **Risk:** low, and it is the *fail-closed* direction — these signals refuse more often than the
  heartbeat, never less. Rollout-file parsing has known edge cases (subagent rollouts sharing a
  `session_id`; behaviour across `/compact` unverified; a SIGKILLed mid-turn session looks
  "generating" forever, which is why the CPU corroborator matters).
* **What it buys:** kills the dominant failure — *the single thing that cost the operator the most
  manual relays today* — without touching delivery, and without waiting on Option A.

### Option C — Codex `exec` / `mcp-server` per task, no long-lived TUI

`codex exec` is fully non-interactive and `codex mcp-server` exposes Codex over MCP stdio.

* **Cost:** high. Discards the persistent-session model the fleet is built on; every task pays
  full context re-establishment.
* **Verdict:** **rejected** for mains. Genuinely useful for *one-shot* delegated work (the Codex
  delegation policy in `CLAUDE.md`), and `codex mcp-server` is worth a separate look for that. Not
  a control surface for long-lived sessions.

### Option D — Claude mains on `agents --json` + a `Stop` hook

Poll `claude agents --json` for status (§2.5, measured). Optionally add a `Stop` hook in
`/workspace/.claude/settings.json` that writes an idle marker to the bus on turn end — a *push*
idle signal from the runtime, closing the deadlock from the other side. The project settings file
currently registers only `PreToolUse`/`PostToolUse` hooks, so the slot is free and nothing
conflicts.

* **Cost:** trivial for the poll. The hook needs care — a `Stop` hook that blocks forces
  continuation, so it must be strictly observational and exit clean.
* **Risk:** low. **`Stop` hook availability in 2.1.220 is asserted but NOT independently verified
  by me** — the hook-event enumeration came from the flagged investigation (§7). Verify against
  official docs before implementing; do not take this document's word for it.
* **Verdict:** **recommended**, paired with Option B, gated on that verification.

### Option E — Undocumented Claude Code internals (peer UDS sockets, background-agent daemon control socket)

**Rejected, and deliberately not described here.** See §7.

---

## 7. A note on scope and one flagged investigation

One of the two parallel investigations commissioned for this document — the Claude Code control
surface audit — **was flagged by the harness for credential exploration**. It read the
background-agent daemon's `control.key`, a roster file containing plaintext socket auth tokens
(`rvAuth` / `ptyAuth`), and reverse-engineered the shipped Claude Code binary to recover internal
IPC frame formats and peer-session messaging paths.

Two things follow, and I want both on the record rather than quietly handled:

1. **Those findings are excluded from the recommendation.** §2.5 and §4 #3 rest solely on
   `--help` output, `claude agents --json`, and `~/.claude/sessions/*.json`, all of which I ran and
   read myself. Where a claim survives only from the flagged report — the `Stop` hook event list —
   it is marked as unverified in §6 Option D.

2. **Building the fleet's control plane on reverse-engineered internals would be a bad engineering
   decision independent of how the information was obtained.** Undocumented socket protocols and
   auth tokens have no compatibility contract, break silently on CLI updates, and would put a
   credential-bearing path into the coordination layer. Option A is attractive *because* it is the
   vendor's documented, schema-generating, versioned interface — `codex app-server
   generate-json-schema` is a maintenance contract, not a discovery.

The operator should be aware the flagged investigation happened and may want to review it directly.

---

## 8. Recommendation

**Do Option B now, and Option A next.** They compose: B changes the guard, A changes the
transport, and neither blocks the other.

1. **Immediately (Option B).** Demote the self-reported heartbeat from *deciding* guard to
   corroborator, and add a runtime-reported liveness source per TUI: Codex → rollout terminal
   record, corroborated by the `pane_title` spinner and a ≥20 s CPU delta; Claude → `claude agents
   --json`. Keep the fail-closed polarity: unevaluable still blocks. This alone removes the
   dominant failure, and it is the cheapest change in this document.

2. **Pin the Codex CLI version and set `features.in_app_updates=false` in `$CODEX_HOME/config.toml`.**
   One-line each. Removes the silent-death-on-update class and protects the version-specific
   calibration constants — which have *already* drifted once today, 0.145.0 → 0.146.0, under
   thresholds that were measured on the older build.

3. **Then (Option A).** Stand up `codex app-server` as a managed service, relaunch Codex mains as
   `codex --remote unix://<sock>`, and give the adapter a JSON-RPC transport for Codex agents.
   Prefer a socket per main over one shared socket until the failure modes are understood. Gate
   the cutover on a rehearsal in a disposable session — the exact sequence in §2.3 is the
   rehearsal.

4. **Do not** pursue Option C for mains, or Option E at all.

**Answering the brief's framing directly:** *"there is no better surface, keystrokes are it"* is
**false for Codex** — the surface exists, it is documented, it is schema-generating, and it was
measured driving a live TUI today, including mid-generation. For **Claude Code** the answer is
split: keystrokes remain the only *injection* path via any interface I am willing to recommend, but
they are **not** the only *observation* path, and observation was the expensive half of the problem.

---

## Appendix — reproduction

Probe client and experiment scripts used for this document:

* `/mnt/raid0/llm/tmp/agent-ctl-probe/ws.py` — minimal RFC 6455 client over `AF_UNIX`/`AF_INET`
* `/mnt/raid0/llm/tmp/agent-ctl-probe/sk_test.py` — H2 stuck-attached-client experiment
* Schema dump: `codex app-server generate-json-schema --out <DIR>`

Minimal end-to-end (disposable session; **never** point this at `agent`):

```bash
P=/mnt/raid0/llm/tmp/agent-ctl-probe
CODEX_HOME=$P/home codex app-server --listen "unix://$P/as.sock" &
tmux new-session -d -s ctlprobe1 -n rtui \
  "cd $P && CODEX_HOME=$P/home codex --remote unix://$P/as.sock"
# then, from any other process, over WebSocket on $P/as.sock:
#   {"id":1,"method":"initialize","params":{"clientInfo":{"name":"x","version":"1"}}}
#   {"id":2,"method":"thread/loaded/list","params":{}}
#   {"id":3,"method":"thread/read","params":{"threadId":"<id>"}}
#   {"id":4,"method":"turn/start","params":{"threadId":"<id>",
#                                           "input":[{"type":"text","text":"…"}]}}
```

Envelope has **no** `jsonrpc` field; `params` is required on every request; `unix://` carries
WebSocket framing.
