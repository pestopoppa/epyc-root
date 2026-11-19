# Architect-general HIP loader fixture bank

This packet captures four prospectively pinned v10 production responses on
one architect-general HIP shape. It retains the three Qwen3.8-Flash-Next
UD-IQ4_XS shards, registered template, MI210 with 24 offloaded layers, CPUs
184–191, 4096 context, one slot, split f16 KV and explicit no-spec. The new
shape recipe pins verbosity 5 and a byte-identical local copy of the
registered template. All four requests run on that same recipe and server.

The JSON fixture prompt spells out the types for the existing `route`,
`enabled` and `replicas` fields. The shared comparator requires string
amber, boolean true and integer 3 with a clean stop. Code, reasoning and
prose retain their original request bytes and their prospectively declared
semantic and finish checks. Native admission requires exact request and
response bytes, token and cold-prefill evidence, two distinct same-PID
in-request MI210 samples per request, pinned library mappings and process,
listener and KFD cleanup. The loader fixture also requires both witnessed
tensor names in the unique mapped serving phase.

The CPU diagnostic refusal and original HIP preparation are pinned source
receipts. The CPU result supplies no HIP evidence. A native semantic refusal
is retained without automatic retry. C13 requires fresh candidate capture
after the complete seven-profile bank seal and its own native HIP loader
witness. The publisher smoke uses a genuine v10 HIP Qwen3-0.6B completion.

The scratch path and limits are pinned in `row.spec.json`. Exact archive
files can be restored under their original names and verified with
`sha256sum -c SOURCE.sha256`. The pregrant receipts pin model weights
and runtimes without reading weight bytes during a grant.
