# Jet-Long gate A (in-window identity, native window 262144)

Generated 2026-10-06 09:28:46. Arms: S = production binary; JOFF = jetlong binary, no flag; JON = jetlong binary, --jetlong-window 2048 --jetlong-native 262144.
Compared vs S: byte-identical text, predicted_n, finish, and per-request draft_n / draft_n_accepted (MTP acceptance).

| arm | records | text identical | tokens(n) identical | draft_n/accepted identical | 34k probe identical | total draft_n | total accepted |
|---|---|---|---|---|---|---|---|
| S | 41 | 41/41 | 41/41 | 41/41 | yes | 4217 | 2866 |
| JOFF | 41 | 41/41 | 41/41 | 41/41 | yes | 4217 | 2866 |
| JON | 41 | 41/41 | 41/41 | 41/41 | yes | 4217 | 2866 |

No divergences.

## Verdict: PASS

PASS requires JON and JOFF byte-identical to S on all 40 short prompts, equal MTP draft_n/accepted, and the 34k probe identical (41 records each).
