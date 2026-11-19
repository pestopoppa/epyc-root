# KPF-18 checkpoint restore witness

`restore_witness.attest` parses the native `SLT_TRC` checkpoint restore event from the P1 server. It requires independently obtained task and slot IDs and an expected checkpoint position, and refuses missing, ambiguous or inconsistent events. The parser alone does not bind an HTTP request, verify the mapped binary, prove physical placement or establish a correctness verdict.

The historical `a1f0c8cf9` server emits the event immediately after checkpoint state is loaded. With fork mode enabled its response timings expose `id_task` and `id_slot`; a caller must preserve and cross-check those values, capture the relevant native log at trace verbosity, and verify the running mapped server library against the intended build. The historical `libllama-server-impl.so` inspected for this format had SHA-256 `58e8905f269b9e6f6f38354f826ea83cbaf9b7f9a9d76e502ec54840394f9269`.

Run the isolated parser tests with `python3 -m unittest discover -s docs/reports/kv-cache/kpf18-restore-witness-20261105 -p 'test_*.py'`. These model-free tests do not qualify a live inference run.

## 2026-11-19 fail-closed restore parsing

Reproduced two pre-fix false accepts: a valid restore followed by a malformed
restore for the same task/slot, and `pos_min=2048` with `pos_max=1023`. The
parser now counts attributed restore headers before parsing payloads, refuses
malformed/truncated payloads and trailing garbage, and requires
`0 <= pos_min <= pos_max`. Valid nonzero sliding-window minima remain allowed;
foreign task payloads do not attest or invalidate this request.

Eight model-free unittest methods PASS, including malformed events alone and
on either side of a valid event, invalid numeric sizes, impossible position
ranges, foreign malformed events and a valid sliding-window range. No native
request, GPU smoke, placement match or parent completion is claimed.
The existing item-2 A/A implementation and retained 0/12 zero-floor result
remain unchanged; a fixed-placement floor cannot resolve different placement.

Source SHA-256 after this repair:

- `restore_witness.py`: `02b2e3191a5313c3604b4e06df9e824a84aa5d4e8014495dbc6c1b3bcc3c1ddd`
- `test_restore_witness.py`: `fcb6ed8625f22fbc3ff43151735daf7ee21d1cb422604c1e61892d5cecff87e9`
