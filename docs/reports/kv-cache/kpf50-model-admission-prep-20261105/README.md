# KPF-50 stat-only admission component

Untested isolated component, prepared without model reads or target exposure. Run `python3 -I check_models.py` only when the owning packet is ready for qualification. It reads its sealed small receipt and own source, then uses stat on the two fixed model paths. The runtime receipt contains no weight digest. Existing pregrant provenance remains in the original binding receipt; PREPARATION.json binds that receipt without copying its model hashes into runtime inputs.

No launcher, smoke, target process, or publication was performed. This does not make the full profile row ready. Remaining integration: self-contained runner/helper/profiler seals, strict captured-birth descendant cleanup, grant wrapper and completion contract, durable no-redraw target exposure ledger, and a separate four-CPU publisher smoke branch incapable of invoking the target. Existing clock qualification must be reused. Do not modify or redraw historical windows.

Metadata equality cannot detect content changes that preserve all recorded stat fields. The owning runtime must preserve the preverified custody assumption and compare metadata before and after model use; do not claim content verification from this checker alone.
