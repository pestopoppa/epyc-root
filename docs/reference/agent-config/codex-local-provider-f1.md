# Opt-in Codex profiles for local llama-server (UFH14-B1c)

**Status: PREPARED for root review; not installed or activated.** Keep the existing
hosted top-level `model` and related settings unchanged. The local providers below are
available only when a user explicitly selects a matching profile.

## User-level provider definitions

Add these tables to `$CODEX_HOME/config.toml` (normally `~/.codex/config.toml`):

```toml
[model_providers.qwen-gpu]
name = "Local llama-server (MI210, Qwen3.8-27B)"
base_url = "http://127.0.0.1:8083/v1"
wire_api = "responses"
requires_openai_auth = false
# UFH14-B1 unmeasured fallback; resolver overrides this per invocation.
stream_idle_timeout_ms = 14400000

[model_providers.qwen-local]
name = "Local llama-server (EPYC CPU, Qwen3.8-Flash-Next)"
base_url = "http://127.0.0.1:8074/v1"
wire_api = "responses"
requires_openai_auth = false
# UFH14-B1 unmeasured fallback; resolver overrides this per invocation.
stream_idle_timeout_ms = 14400000
```

## Explicit profile files

For Codex CLI 0.165, `--profile qwen-gpu` loads exactly
`$CODEX_HOME/qwen-gpu.config.toml`; `--profile qwen-local` loads
`$CODEX_HOME/qwen-local.config.toml`. Create these two files:

`$CODEX_HOME/qwen-gpu.config.toml`:

```toml
model = "qwen3.8-27b"
model_provider = "qwen-gpu"
```

`$CODEX_HOME/qwen-local.config.toml`:

```toml
model = "qwen3.8-flash-next"
model_provider = "qwen-local"
```

These are the documented profile filenames, not files Codex discovers by arbitrary
filename search. Leave the existing top-level hosted default untouched. Do not combine
these with legacy `[profiles.qwen-gpu]` / `[profiles.qwen-local]` tables: Codex 0.165
rejects `--profile` when those legacy tables are present.

## Per-invocation derived overrides, fail closed

Use the existing resolver on every local invocation. The provider ID and URL must match
the selected profile. This wrapper checks the resolver exit code, JSON, and argv shape
before starting Codex; its `execvp` forwards the helper's array without joining or
re-quoting it. A resolver failure cannot fall through to a Codex launch. Save the complete
block as an executable named `codex-local-f1-exec`; invoke it with a provider, matching
URL, and prompt arguments, for example:
`./codex-local-f1-exec qwen-gpu http://127.0.0.1:8083/v1 "Review this patch"`.

```bash
#!/usr/bin/env bash
set -euo pipefail
provider=${1:?usage: codex-local-f1-exec <qwen-gpu|qwen-local> <base-url> <prompt...>}
base_url=${2:?usage: codex-local-f1-exec <qwen-gpu|qwen-local> <base-url> <prompt...>}
shift 2
if (($# == 0)); then
    echo "a prompt is required" >&2
    exit 2
fi
python3 - "$provider" "$base_url" "$@" <<'PY'
import json
import os
import subprocess
import sys

provider, base_url, *prompt_args = sys.argv[1:]
expected_urls = {
    "qwen-gpu": "http://127.0.0.1:8083/v1",
    "qwen-local": "http://127.0.0.1:8074/v1",
}
if expected_urls.get(provider) != base_url:
    raise SystemExit("provider and base URL do not match a documented profile")
resolver = "/workspace/repos/epyc-inference-research/scripts/kernel_rnd/autokernel/loop/actor_serving.py"
result = subprocess.run(
    [sys.executable, resolver, "--base-url", base_url, "--codex-provider", provider],
    check=True, capture_output=True, text=True,
)
payload = json.loads(result.stdout)
overrides = payload.get("codex")
if type(overrides) is not list or not overrides or len(overrides) % 2:
    raise SystemExit("resolver returned an invalid Codex argv array")
allowed = {
    f"model_providers.{provider}.stream_idle_timeout_ms",
    "model_context_window",
    "model_auto_compact_token_limit",
}
for flag, assignment in zip(overrides[::2], overrides[1::2]):
    if flag != "-c" or not isinstance(assignment, str) or "=" not in assignment:
        raise SystemExit("resolver returned an invalid Codex override")
    if assignment.split("=", 1)[0] not in allowed:
        raise SystemExit("resolver returned an unexpected Codex setting")
os.execvp("codex", ["codex", "--profile", provider, *overrides, "exec", *prompt_args])
PY
```

The helper derives `stream_idle_timeout_ms` from live server `/props` plus serving-call
prefill records, falling back to 14,400,000 ms when unmeasured. When `/props` supplies a
per-request context, it also emits `model_context_window` and
`model_auto_compact_token_limit` from that metadata. It emits no context/compaction values
when server metadata is unavailable; never add model-window constants here. The current
Codex projection has no output-token-limit override. Do not invent one.

## Scope and limits

Codex documents `stream_idle_timeout_ms` as an SSE-stream idle timeout (default 300,000 ms).
It is not a separate header/pre-first-event timeout, so this profile does not claim to
cover silence before an SSE response begins. OpenCode's distinct `headerTimeout` and
`chunkTimeout` remain at 14,400,000 ms in the current global config. Its actor-seat path
also derives context/output limits per call; the static global config does not.

The frozen llama-server source registers `POST /v1/responses`; its direct handler converts
Responses input to Chat Completions and emits Responses output. Router mode maps the same
route to its proxy handler. Codex 0.165's supported `wire_api` value is `responses`. This
source contract establishes route/protocol compatibility only; it does not test a model
or activate either endpoint.

## Model-free checks (2026-10-31)

- Installed Codex CLI: 0.165.0. Its `app-server --print-startup-config --strict-config`
  accepts the two provider tables, `wire_api="responses"`,
  `requires_openai_auth=false`, and `stream_idle_timeout_ms=14400000`, with exit 0.
- The same CLI rejects `--profile` on `app-server --print-startup-config`; it reports
  profiles apply to runtime commands and `debug prompt-input`. Therefore strict startup
  parsing and profile selection cannot be combined in that command.
- With isolated `$CODEX_HOME`, `codex --profile qwen-gpu debug prompt-input` and the
  `qwen-local` equivalent both exited 0 and loaded their profile files without a model
  request. The CLI's strict app-server parser separately accepted each profile's effective
  model/provider plus its base provider's `responses`/idle settings (rc 0 for both); the
  current CLI does not expose a single command that combines strict parsing with profile
  selection.
- Combining `[profiles.qwen-gpu]` / `[profiles.qwen-local]` with `--profile` failed in
  0.165.0 with an explicit legacy-profile conflict; those tables are not used here.
- Fail-closed wrapper checks: resolver nonzero exit and malformed JSON both stopped before
  `execvp`; success forwarded the exact helper argv array as separate arguments, including
  an override with spaces in the prompt preserved as one argv item.
- Existing resolver results: 8074 emitted exactly
  `[-c, model_providers.qwen-local.stream_idle_timeout_ms=14400000]` with unknown context,
  0 prefill samples; 8083 emitted exactly
  `[-c, model_providers.qwen-gpu.stream_idle_timeout_ms=14400000]` with unknown context,
  4 samples. Both `/props` endpoints refused connection, so no dynamic context/compact
  values were emitted. These observations are transient, not hardcoded config values.
- Active `/home/node/.codex/config.toml` has no local provider. No live config was changed.

References: current source clause `handoffs/active/agentic-serving-harness-fixes.md` UFH14-B1c;
resolver `scripts/kernel_rnd/autokernel/loop/actor_serving.py`; Codex config reference:
https://developers.openai.com/codex/config-reference.
