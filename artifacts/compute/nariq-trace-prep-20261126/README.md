# NARIQ trace preparation (partial, 2026-11-26)

The corpus requested by NARIQ-TRACE-CORPUS-1 is not yet produced. This lane was
instructed to use existing data and not run models, servers, or inference. The
box specifically requires newly generated local-model sessions. The source
vault at `/mnt/raid0/llm/cloud-llm-vault` contains foreign cloud sessions; they
are only a domain control and cannot substitute for local-model output. The
box records that no local BF16- or Q8-written agent logs were found; this lane
did not conduct an exhaustive independent search proving their absence.

The BF16 source shards are present at
`/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507/`; Q8 is present at
`/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507-GGUF/Qwen3-4B-Instruct-2507-Q8_0.gguf`.
Their presence does not establish the generating build or token counts.

`validate_traces.py` validates a proposed intermediate JSONL: each line is one
unique session with `session_id`, `split` (`calibration` or `heldout`),
`token_ids` (nonnegative integer IDs), and `model_written` (one integer 0 or 1
per token). It reports the input digest and counts. A producer must derive masks
from actual tokenization and role boundaries, and establish the prediction-token
offset and exact file contract with NARIQ-KLD-MASK-1. This validator cannot prove
the labels, tokenizer identity, independence of distinct session IDs, absence
of duplicate content, or compatibility with llama-perplexity. Its synthetic
test fixture is not a corpus. Never treat passing validation as the box's
done-when evidence.

The experimental `experimental/ear-kld-column-20261022` branch inspected here
has no per-token mask implementation. NARIQ-KLD-MASK-1 remains a separate open
gate. The local corpus, frozen calibration/heldout splits, generating model and
build identities, token counts, hashes, consumer contract, runnable declarations
and their deployed-tool rehearsals remain required before NARIQ-IMX-1 is ready.
No row was published or claimed.
