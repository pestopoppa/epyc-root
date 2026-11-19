# KPF-50 no-redraw preparation

This isolated runner copy records an exclusive durable start marker before the
first item-7 request and refuses generic resume or repeat exposure. A separate
validator checks structural binding of prior completion receipts. Thirteen
model-free tests passed, including marker ordering and retry refusal.

The current runner does not produce the required typed completion receipts.
The validator does not establish scientific validity, clock qualification, or
full descendant cleanup. No KPF-50 run or publication follows from this work.
