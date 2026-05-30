# Bug / UX: `llama-completion` silently switches to conversation mode when GGUF embeds a chat template; `llama-cli` no longer accepts `--no-conversation`

**Target repo**: [`antirez/llama.cpp-deepseek-v4-flash`](https://github.com/antirez/llama.cpp-deepseek-v4-flash)
**Tip tested**: `2f2d44052`
**Severity**: MEDIUM — silent workload change for bare-completion users; identical CLI invocation produces semantically different decode depending on GGUF metadata
**Component**: `tools/completion/completion.cpp:213` + `tools/main/main.cpp` (`--no-conversation` removal)
**Filed by**: EPYC inference research project, 2026-05-30

## Summary

Two related observations:

1. `llama-completion` auto-enables conversation mode when the loaded GGUF has `tokenizer.chat_template` embedded, unless `-no-cnv` is passed explicitly. The default flips based on model metadata, not flag presence — so the same `-p "..."` invocation runs raw completion on one model and chat-templated multi-turn on another. The behavior is documented in the code comment but not in the default `--help` output, and it bites anyone migrating a bench harness from a chat-template-less model to V4 (which embeds at `kv[57]`).

2. `llama-cli` no longer accepts `--no-conversation` at all on this fork — it emits `"--no-conversation is not supported by llama-cli, please use llama-completion instead"` and then drops into interactive chat mode anyway, ignoring the flag. On `EOF` from non-interactive stdin, the interactive loop spews `> ` prompts to stdout indefinitely (we observed 5.4 GB / 2.88 B lines in 10 minutes before a `timeout` killed it).

Combined, the two changes break any non-interactive bench/smoke harness that uses `llama-cli -p ... --no-conversation` (the mainstream pattern). Migrating to `llama-completion` is straightforward once known, but the discoverability is poor and the error message is misleading (it suggests using `llama-completion`, but doesn't say `-no-cnv` is also needed there if the model embeds a template).

## Reproduction

### (a) `llama-completion` silent auto-cnv

```bash
# V4 GGUF embeds tokenizer.chat_template; conversation mode auto-on:
$ llama-completion -m DeepSeek-V4-Flash-Q4*.gguf -t 96 -c 8192 \
    --temp 0 --seed 1 -n 4 -p "Hello," --no-mmap --mlock -fa 1
# → loads model, prints "auto enable conversation mode if chat template is
#   available; disable it with -no-cnv", then runs the prompt through the
#   template instead of bare completion.
```

Same model + same flags + `-no-cnv` produces raw `"Hello," → "I'm sorry,"` completion (4 tokens, clean exit). The two outputs are not equivalent.

### (b) `llama-cli --no-conversation` removal

```bash
$ llama-cli -m DeepSeek-V4-Flash-Q4*.gguf -t 96 -c 8192 --temp 0 --seed 1 \
    -n 4 -p "Hello," --no-conversation -ngl 0 -fa 1 --mlock --no-mmap
# → prints "--no-conversation is not supported by llama-cli, please use
#   llama-completion instead", LOADS THE MODEL ANYWAY, drops into
#   interactive chat at the > prompt, and on stdin EOF runs an infinite
#   loop emitting `> \n` (we observed 5.4 GB / 2.88 B lines in 10 min
#   before SIGTERM).
```

## Expected behavior

For (a): conversation mode should be opt-in via an explicit flag, not implicit-on based on model metadata. If keeping the auto-enable behavior, the default should be loud (warning + a sentence-level prompt in `--help` for the auto-cnv rule, not just a code comment).

For (b): either (i) accept `--no-conversation` as a deprecated alias that turns off conversation mode (mainstream behavior), or (ii) refuse to start with a clear error if the flag is unsupported. Currently it loads the model + enters interactive mode + EOF-loops, which is the worst of all worlds — wasted load time + runaway output + non-zero core damage to the operator's morale.

## Actual behavior

See reproduction above.

## Root cause

For (a): `tools/completion/completion.cpp:213`:

```cpp
// auto enable conversation mode if chat template is available
const bool has_chat_template = common_chat_templates_was_explicit(chat_templates.get());
if (params.conversation_mode == COMMON_CONVERSATION_MODE_AUTO) {
    if (has_chat_template) {
        LOG_INF("%s: chat template is available, enabling conversation mode (disable it with -no-cnv)\n", __func__);
        params.conversation_mode = COMMON_CONVERSATION_MODE_ENABLED;
    } else {
        params.conversation_mode = COMMON_CONVERSATION_MODE_DISABLED;
    }
}
```

The auto-on rule is principled (chat templates strongly imply chat workflows) but the workload change is silent at the bash-pipeline level — a script that worked yesterday on a non-chat-template model fails today on V4 with the same flags. `LOG_INF` lands in stderr; a quiet bench harness wouldn't surface it unless it specifically watches stderr.

For (b): the V4 fork removed the `--no-conversation` mapping from `llama-cli`'s argparse but did not exit non-zero or refuse to start when an unrecognized but legacy flag is seen. The model still loads + the binary still runs.

## Suggested fixes (in priority)

1. **For (b)**: make `llama-cli` exit 1 immediately when it sees `--no-conversation`, with a one-line "use llama-completion -no-cnv instead" message. Don't load the model. This is the cheap fix and stops the EOF-spew failure mode.

2. **For (a)**: keep auto-cnv-on as the default for chat-template-bearing GGUFs but emit a single-line WARN to stderr (not INF), and document the rule in `--help`'s `-no-cnv` description ("DEFAULT: off, unless GGUF embeds tokenizer.chat_template, in which case the default is on").

3. **Alternative for (a)**: invert the default — keep `COMMON_CONVERSATION_MODE_DISABLED` as the auto-fallback, require `-cnv` or `--conversation` for chat mode. This breaks the auto-conv ergonomics for desktop chat users but eliminates the silent semantic change. (Probably too invasive; option 2 is a better tradeoff.)

## Workaround in use downstream

EPYC inference research project (2026-05-30):

- All V4 smoke + bench harnesses pass `-no-cnv` explicitly to `llama-completion`
- `llama-cli` is not used at all for V4 (its removed `--no-conversation` flag is a footgun; `llama-completion` is the only sanctioned non-interactive path)
- Handoff `handoffs/active/deepseek-v4-flash-cpu-port.md §Throughput gate` explicitly names the tool + flag combination

## Environment

(same as bug 01)
