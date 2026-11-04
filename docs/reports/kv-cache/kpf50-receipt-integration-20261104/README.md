# KPF-50 receipt integration candidate

This isolated runner copy calls the typed receipt producer after the fanout,
server stop and after-clock step, and uses the hardened consumer to refuse
advancing past an invalid or tampered prior receipt. It requires a completed
fan sequence, a verified server-stop record, and five independently prepared
typed evidence files in the durable lineage directory; it never manufactures
cleanup, clock, outcome or trace evidence. The start marker still precedes the
first target request. Twelve model-free tests passed, covering the integrated
publication boundary, incomplete inputs, tampering and step ordering.

This is a review copy, not a sealed or publishable runner. No implemented
component yet produces the required independent typed evidence from actual
processes; server-only death is not full descendant cleanup. Structural
receipts do not establish scientific validity, clock alignment or protection
against same-UID mutation races. Real trace capture, device/process binding,
cleanup proof, valid clock witnesses, full integration and native qualification
remain open. No model, profiling or publisher run was performed.
