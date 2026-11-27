# Six-case direct-main execution accounting

Five cases passed after one paid direct turn; TU-GR-1 passed after a second paid repair turn. This selected cohort contains seven fresh gpt-6.1-sol/low CLI turns. The failed first TU attempt remains fully counted.

| Case | Paid turns to acceptance | Input | Cached | Uncached | Output | Reasoning subset | CLI seconds summed |
|---|---:|---:|---:|---:|---:|---:|---:|
| PAW-5 | 1 | 183,698 | 149,504 | 34,194 | 2,900 | 51 | 66.922348 |
| DS41-W-66 | 1 | 343,820 | 303,616 | 40,204 | 2,056 | 80 | 74.823704 |
| NARIQ-LIBTRELLIS-MAP-1 | 1 | 158,668 | 130,944 | 27,724 | 3,859 | 10 | 89.898506 |
| PFXC-A3 | 1 | 224,938 | 201,088 | 23,850 | 5,051 | 22 | 111.710705 |
| TU-GR-1 | 2 | 172,616 | 152,448 | 20,168 | 2,529 | 123 | 191.404095 |
| MM-5 | 1 | 142,565 | 129,536 | 13,029 | 2,973 | 93 | 140.117489 |

| Execution scope | Input | Cached | Uncached | Output | Reasoning subset | CLI seconds summed |
|---|---:|---:|---:|---:|---:|---:|
| Initial six turns | 1,168,733 | 1,017,344 | 151,389 | 18,908 | 328 | 603.314610 |
| Additional TU repair | 57,572 | 49,792 | 7,780 | 460 | 51 | 71.562237 |
| All seven turns | 1,226,305 | 1,067,136 | 159,169 | 19,368 | 379 | 674.876847 |

Reported reasoning is already included in output. Total cache-write input is 0 in the raw usage records; an absent field would remain unavailable. The duration sum includes CLI tool/runtime work and is not parallel batch elapsed or isolated model inference time.

Checker history remains visible: PAW moves from original rc1 to formatting-checker v3 rc0 on identical bytes. PFXC retains original rc0 and a later exact-events v4 rc0 replay of the same direct artifact. W66 retains its isolated dependency/context check; NARIQ retains its selected source checker and source/web audit. These regrades add no measured direct-main execution turn to these receipts; their broader work cost remains outside these vectors. Raw measurement review flags are unchanged; committed source/scope reviews bind the actual event and candidate hashes.

These are main-only execution vectors. Manager work, setup, review, checker repair and experiment coordination are neither priced as free nor included. Native A3B execution remains separate. The separately recorded NARIQ paid guidance-1 review (123,494 input / 91,008 cached / 32,486 uncached / 1,016 output, including 21 reasoning; 95.819931 CLI seconds) is explicitly excluded from every main-only total; its candidate was unchanged.

ACCOUNTING.json binds raw usage, schemas, candidate/receipt hashes and committed reviews at 47139dc8f2206e9149cf403269c33b6531791c80. TURNS.tsv preserves all seven turn vectors; CASES.tsv groups them by logical task. Extraction performs no model/candidate reexecution and changes no original files.

Next: main integrates these execution-only vectors with separately measured A3B, guidance and coordination evidence.
