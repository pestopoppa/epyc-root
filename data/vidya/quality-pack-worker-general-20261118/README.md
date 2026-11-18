# Worker-general quality-pack input preparation

Row `handoff-vidya-quality-pack-worker-general-20261118` was published after a
four-CPU publisher smoke passed on CPUs 116–119. The smoke captured one genuine
v10 Qwen3-0.6B Q8_0 no-spec completion and verified its exact request and
response bytes, returned token IDs, process exit, and listener closure. The
full row remains open. [Publication and capture receipt](receipt.json)

The full row is designed for four fixed worker requests per arm on isolated
v10 and C13 CPU servers with Qwen3.6-35B-A3B-MTP-Q8_0, q8_0 KV, the registry
chat template, and MTP cap 4. The worker registry supplies the model and
drafting recipe. Compiled serving priors describe the deployed alias with
speculation disabled. The packet reuses existing model hash receipts and
checks the model files by recorded filesystem identity before launch.

The prior frontdoor JSON response still differs in content and token IDs
between arms. Seven-profile coverage, strict comparison and planning-context
acceptance remain open. [Earlier frontdoor capture](../quality-pack-native-20261118/full-capture/receipt.json)

Some JSON files contain nanosecond filesystem timestamps. Their
`.original-bytes.json` envelopes preserve the original bytes in `bytes_b64`
and the original `sha256`. The runnable packet and its `SOURCE.sha256` reside
in the scratch path recorded in `row.spec.json`.
