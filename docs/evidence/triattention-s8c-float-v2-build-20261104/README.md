# S8-c float-corrected candidate CPU build

The row completed rc=0 after the ggml-base checkpoint and CPU server build. The experimental source is frozen production tip `ffc1bac82eeca6f9099e1ccd9ba49703c460a115` plus patch `7612c84004793847a77237d8881830a8f17041625be28bd409591289f62298dc`; all seven artifact digests were verified before filing. Server binary SHA-256: `2b62285c98f28d02dde77acdbccc119acf00e6a7197335beab0fb514f27b75e6`.

This is compilation evidence only. It does not establish real-cache correctness, model quality, GPU behavior, or deployment readiness. The candidate remains experimental and conservatively rejects unsupported layouts. Embedded paths in the original records are retained as provenance.
