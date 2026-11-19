# Qwen4exp CPU loader diagnostic

This isolated row asks whether pinned v10 and C13 CPU images load the same model
shards and each serve one fixed JSON request. The original GGUF stores two
first-layer F32 hyper-connection norm tensors flat at 10,240 elements. The
pinned v10 source loads them flat. The pinned C13 source requests 2,560 × 4
through the loader's reshape path. The supplied witness binds the tensor
headers and source evidence. Successful native health, matching tensor-load
logs and a generation response on each verified CPU executable will establish
native exercise of the respective paths. Runtime dimensions are inferred from
the source bound to each binary.

This retry scopes native load evidence to the single `mmap = true` phase,
from the loader start through the next context-construction marker. The
pinned runtimes may first do a no-allocation fit probe with mmap disabled.
Both probes can print the same tensor names. The capture records phase
boundaries, one exact line per witnessed tensor in the mapped phase, and the
full raw log digest.

Native request and response checks precede the exact same JSON semantic
validation. When both arms pass native checks and a reply fails the expected
finish or JSON check, the result records `loader_exercised_response_refused`
with both capture digests and per-arm checks. The terminal completion
predicate requires both arms to pass the original response expectations.

The row uses one 24-CPU quarter, 112 GiB host RAM and a minimum 1,650-second
grant. Each arm has one 460-second startup bound, one 240-second request bound
and captured-PID cleanup. The v10 response and custody are sealed before C13
starts. The small-model v10 CPU publisher smoke uses four CPUs and its own
45-second startup and 30-second request bounds.

This output is an isolated CPU diagnostic. The required architect-general HIP
profile has its own queued row and prospective production bank. The CPU
diagnostic adds no broad-pack coverage, quality-transfer authority or promotion
authority.
