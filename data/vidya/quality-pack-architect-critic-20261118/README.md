# Architect-critic quality-pack input preparation

Row `handoff-vidya-quality-pack-architect-critic-20261118` was published after
the four-CPU smoke passed on CPUs 116–119. The smoke ran one v10 Qwen3-0.6B Q8_0
no-spec completion and verified the original request and response, eight
returned tokens, the captured process exit, and listener closure.
[Publication and smoke receipt](receipt.json)

The full row is open for four fixed requests per arm on isolated v10 and C13
CPU servers. It uses Qwen3.8-27B Q8_0, the registered chat template with
medium thinking, q8_0 KV, one slot, and 24 CPUs. The model hash matches the
registry, its GGUF has one embedded NextN layer, and the local artifact
registry records MTP draft cap 4. The compiled deployed role uses MI210
DFlash2 cap 7 and four slots. The isolated recipe uses self-draft MTP cap 4
with no sidecar. The grant checks the saved model filesystem identity and the
content hashes of both CPU runtimes.

The earlier frontdoor JSON content and token mismatch remains part of the
broad-pack record. Broad coverage, comparison, and planning-context
acceptance remain open.
[Earlier frontdoor capture](../quality-pack-native-20261118/full-capture/receipt.json)

The `.original-bytes.json` envelopes preserve the exact bytes and SHA-256 of
records with nanosecond timestamps. Decode `bytes_b64` to recover the file
named in the receipt. The staged packet and its `SOURCE.sha256` reside in
the scratch path recorded in `row.spec.json`.
