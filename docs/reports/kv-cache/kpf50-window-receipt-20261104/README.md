# KPF-50 window completion candidate

`window_custody.py` extends the earlier no-redraw marker and validator with `finish`, an exclusive completion writer. It binds the already-durable start marker to five existing evidence files and verifies their hashes, lineage, typed outcome and verified-death fields before writing and syncing a completion receipt. Missing, modified or symlinked evidence is refused. Clock and trace evidence receive structural and digest checks; scientific validity and clock calibration remain separate. A partial completion marker remains terminal and is not overwritten.

Seven model-free tests cover valid advancement, duplicate completion, missing or changed evidence, bare clock or trace metadata, wrong lineage, symlinked evidence, unverified cleanup and interrupted marker refusal. Run `python3 -m unittest discover -s docs/reports/kv-cache/kpf50-window-receipt-20261104 -p test_finish.py`.

This candidate does not itself produce measurements or verify their scientific validity. The actual KPF-50 runner does not yet collect the typed outcome, full-descendant cleanup, bracketed clocks and trace-manifest evidence required by the contract; this writer is deliberately not integrated until those records are qualified. No inference, GPU execution, launcher publication or profile verdict follows.
