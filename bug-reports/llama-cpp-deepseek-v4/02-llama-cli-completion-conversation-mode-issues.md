# Bug cluster: `llama-cli` conversation-mode handling + `llama-completion` auto-cnv UX

**Target repo**: [`antirez/llama.cpp-deepseek-v4-flash`](https://github.com/antirez/llama.cpp-deepseek-v4-flash)
**Tip tested**: `2f2d44052`
**Filed**: EPYC inference research project, 2026-05-30 (revised after operator audit)
**Component**: `tools/cli/cli.cpp`, `common/arg.cpp`, `tools/completion/completion.cpp`

Three distinct sub-bugs, related but independently fixable. Severities differ.

> **Audit note (2026-05-30)**: this report's first draft conflated three issues + overstated the help-text gap on the auto-cnv issue. The auto-cnv default is documented at `common/arg.cpp:1505` and `tools/completion/README.md:242` (verified locally). This revision separates the three issues and corrects the help-gap claim.

---

## 2a (HIGH) — `llama-cli` accepts `--no-conversation` then falls through into model loading

### Reproduction

```bash
llama-cli -m model.gguf -p "Hello," -n 4 --no-conversation -no-cnv ...
```

### Expected

`llama-cli` exits non-zero immediately with a clear "use `llama-completion -no-cnv` instead" message, BEFORE loading the model.

### Actual

`tools/cli/cli.cpp:356-359` (V4 fork at 2f2d44052):

```cpp
if (params.conversation_mode == COMMON_CONVERSATION_MODE_DISABLED) {
    console::error("--no-conversation is not supported by llama-cli\n");
    console::error("please use llama-completion instead\n");
}
// falls through into cli_context ctx_cli(params); llama_backend_init(); ...
// → loads the 153 GiB V4 model into mlock'd RAM (~2 min)
// → enters interactive chat mode
// → 2b (below) takes over on EOF stdin → infinite > prompt loop
```

The flag is shared from `common/arg.cpp:1498` between `LLAMA_EXAMPLE_COMPLETION` and `LLAMA_EXAMPLE_CLI` — `llama-cli`'s argparse accepts it, sets `params.conversation_mode = COMMON_CONVERSATION_MODE_DISABLED`, then the CLI-side check above prints a warning but doesn't bail.

### Suggested fixes

**Minimal** (least invasive): add `return 1;` after the two error messages at `cli.cpp:359`.

```diff
     if (params.conversation_mode == COMMON_CONVERSATION_MODE_DISABLED) {
         console::error("--no-conversation is not supported by llama-cli\n");
         console::error("please use llama-completion instead\n");
+        return 1;
     }
```

**Better** (cleaner separation): remove `LLAMA_EXAMPLE_CLI` from the shared `-no-cnv` option in `common/arg.cpp:1498`:

```diff
     ).set_examples({LLAMA_EXAMPLE_COMPLETION, LLAMA_EXAMPLE_CLI}));
+    ).set_examples({LLAMA_EXAMPLE_COMPLETION}));
```

Then register a CLI-only deprecated handler that fails during arg parsing with the same message, so model loading is never reached.

This patch series applies the minimal fix in `02ab-cli.patch`. The better fix is deferred — it touches the LLAMA_EXAMPLE_* dispatch infrastructure and warrants its own PR.

---

## 2b (HIGH) — `llama-cli` infinite `> ` prompt loop on EOF stdin (broader than 2a)

### Reproduction

```bash
echo -n "" | llama-cli -m model.gguf -i -p "Hello"
# OR
llama-cli -m model.gguf -cnv -p "Hello" < /dev/null
```

(Any path that triggers conversation mode + provides EOF on stdin. Including the post-2a fall-through path described above.)

### Expected

EOF on stdin causes a graceful break with a `> EOF by user` message (matching `llama-completion`'s behavior on the same condition) and clean exit.

### Actual

`tools/cli/cli.cpp:469-525` (V4 fork at 2f2d44052) — the interactive loop:

```cpp
while (true) {
    std::string buffer;
    console::set_display(DISPLAY_TYPE_USER_INPUT);
    if (params.prompt.empty()) {
        console::log("\n> ");
        std::string line;
        bool another_line = true;
        do {
            another_line = console::readline(line, params.multiline_input);
            buffer += line;
        } while (another_line);
    } else { ... }
    ...
    // skip empty messages
    if (buffer.empty()) {
        continue;  // ← bug: on EOF, buffer is empty; loop forever
    }
```

`console::readline()` returns `bool` (per `common/console.h:24`), conflating "no more continuation lines" with "EOF reached". On EOF, the do-while exits with `buffer` empty, `if (buffer.empty()) continue;` re-enters the loop, prints `> `, calls `readline` again, returns false immediately, continues. Observed: 5.4 GB / 2.88 B `> \n` lines in 10 min before SIGTERM.

### Suggested fixes

**Minimal**: check `std::cin.eof()` after the do-while:

```diff
     // skip empty messages
     if (buffer.empty()) {
+        if (std::cin.eof()) {
+            console::log("\n> EOF by user\n");
+            break;
+        }
         continue;
     }
```

This matches the message and behavior in `llama-completion` (which we verified outputs `> EOF by user` on stdin EOF during V4 smoke testing).

**Better**: change `console::readline()` to return an enum (`{ MORE, DONE, EOF }`) and handle each explicitly in cli.cpp. Cleaner long-term but a wider API change. This patch series applies the minimal fix in `02ab-cli.patch`.

---

## 2c (LOW) — `llama-completion` auto-cnv notice should be `LOG_WRN`, message should call out the semantic change

### Status

The original draft of this report claimed the auto-enable behavior was undocumented in `--help`. **That was wrong.** Operator audit confirmed:

- `common/arg.cpp:1505`: `--help` text for `-cnv`/`--conversation`/`-no-cnv`/`--no-conversation` ends with `(default: auto enabled if chat template is available)`, and
- `tools/completion/README.md:242`: README documents `(default: auto enabled if chat template is available)` for the same flag cluster

So the rule IS discoverable. The remaining issue is the runtime notice's tone + content: it uses `LOG_INF`, which a non-interactive bench harness will not surface, and the message says only "enabling conversation mode (disable it with -no-cnv)" — it doesn't tell the user that this changes the semantic workload (template applied + multi-turn UI vs raw completion).

### Reproduction

```bash
llama-completion -m model_with_chat_template.gguf -p "Hello," -n 4 ...
# stderr (LOG_INF, often suppressed in headless pipelines):
# main: chat template is available, enabling conversation mode (disable it with -no-cnv)
# → runs the prompt through the chat template + multi-turn workflow
# → bench harnesses migrating from a non-chat-template model silently get
#   different decode characteristics
```

### Expected

Auto-cnv enabled by default for chat-template GGUFs (existing design — keep it; reasonable for desktop chat). But the notice should be:
- A WARNING (visible even with INFO suppressed), and
- Explicit about the semantic change ("raw completion changed to chat mode because the model has a chat template; pass `-no-cnv` for raw prompt completion, or `-st` for a single chat turn")

### Actual

`tools/completion/completion.cpp:213` (V4 fork at 2f2d44052):

```cpp
LOG_INF("%s: chat template is available, enabling conversation mode (disable it with -no-cnv)\n", __func__);
```

### Suggested fix

```diff
-            LOG_INF("%s: chat template is available, enabling conversation mode (disable it with -no-cnv)\n", __func__);
+            LOG_WRN("%s: raw completion changed to chat mode because the model has a chat template; "
+                    "pass -no-cnv for raw prompt completion, or -st for a single chat turn\n", __func__);
```

Severity LOW — the default behavior stands, only the notice changes. This patch series applies the fix in `02c-completion.patch`.

---

## Patches (in this directory)

- [`02ab-cli.patch`](02ab-cli.patch) — `cli.cpp:359` `return 1` after `--no-conversation` warning, plus EOF detection at the empty-buffer guard
- [`02c-completion.patch`](02c-completion.patch) — `completion.cpp:213` LOG_INF → LOG_WRN with semantic-change message

Each patch is independent and applies with `git apply <name>.patch` from the V4 fork root. They can be filed as separate upstream PRs or as one bundled patch series.

## Downstream workaround in use

Bug 02a: EPYC inference research project uses `llama-completion` exclusively for V4 non-interactive work; `llama-cli` is not invoked anywhere in the bench harnesses.

Bug 02b: same — `llama-completion`'s EOF handling is correct, so we never hit the loop.

Bug 02c: `scripts/benchmark/v4_throughput_gate.sh` and `v4_smoke_test.sh` always pass `-no-cnv` explicitly. The handoff `handoffs/active/deepseek-v4-flash-cpu-port.md §Throughput gate` documents the requirement.

## Environment

(see [`01-llama-bench-sched-reserve-assert.md`](01-llama-bench-sched-reserve-assert.md))
