# PIP-02 epoch watcher checkpoint — 2026-10-30

ODL completed native batches: 20. Eleven separately inventoried completed snapshots have 255 pages and lack captured original producer/source identities; they remain ordinary observations, outside strict aggregates. Four of those eleven have zero GT tables and undefined scores.

Paddle: 37 ready shards had 32 complete snapshots and five partial snapshots at audit. The five prospective new generations below preserved the unregistered-original-capture errors; they yielded no new eligible completed shard. Current running table counts 251 distinct verified pages and 78 GT tables.

| Paddle shard | Verified pages / planned | Scored GT tables / planned | Immutable receipt | Receipt SHA-256 |
|---|---:|---:|---|---|
| s011 | 2/5 | 0/0 | `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-watch/epochs/s011/fe2d4fd6e8861846aaa8b83a01733ff6e16b8672cae372b281d6b474bdac55e6/s011.score-receipt.json` | `5e08770ed70409d3a0deadafa4d956e9f417ccf9656cc1aade11c7866ede42ab` |
| s012 | 4/5 | 0/0 | `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-watch/epochs/s012/4fc1708a818e01fe83007cabacdbce90348113eca0be312293723c7582bad1f2/s012.score-receipt.json` | `a1d1f437df0aea0d471b7c6bde70f530b3318a565aacdc6d52b4e069232ac5aa` |
| s013 | 1/5 | 0/0 | `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-watch/epochs/s013/773f435e06d10e041c2d260d3e37b9546e707b9b1101f5279ccf1cd8be33a7ca/s013.score-receipt.json` | `e8db56d16f4238453e89b79816d06bfaa3813c920dc7eb21c56beebeace69c78` |
| s107 | 0/5 | 0/8 | `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-watch/epochs/s107/c61f5a2cff88b66c0a82aedf1ba011ca6832aa2d630825e42435dd11c242ba64/s107.score-receipt.json` | `874cd0b7ad0acf9336a9ac890a52a02b3a513de73ac9126485f388c3229e5d80` |
| s109 | 1/5 | 0/0 | `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-watch/epochs/s109/321bef896778942c00f98865d99146633343851e16a12a52ebd7da6cce3ba7a6/s109.score-receipt.json` | `1ccd9b19f794b434129dc292439549407385b39fdc7f1cc1fd57b9f13e9ab4cd` |

Epoch identity binds per-case finish/request bytes, referenced original captures and registries, selected producer source bytes, source images, plan, configuration and scoring source. Unrelated capture files are excluded from the key. A generation path is write-once and an unchanged epoch is not retried; changed evidence gets a new generation. Older scores and refusal records remain untouched.

Original watchers 2373051 and 2341453 were stopped at an idle mutex boundary and verified absent. Replacement ODL PID 790668 (birth 151477532) and Paddle PID 793354 (birth 151478825) were verified running. CPU admission and scoring use the original 26–27 mutex with admitted CPU 122–123 fallback; no model inference ran.

Validation: `/mnt/raid0/llm/tmp/pip02-vidya-draft/test_epochs.py` verified that referenced capture or case changes create a new epoch while unrelated capture and unchanged polling do not. `/mnt/raid0/llm/tmp/pip02-vidya-draft/test_partial_complete.py` verified a synthetic partial-to-complete transition, original JSON hash preservation, strict receipt acceptance and idempotent renderer. These are fixture checks, not model results.

Artifacts (SHA-256 at checkpoint):

- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/epoch_watch.py` — `62834df23e219d29473ae71345da4eab9106cba9a2266bd62e3b8d1b98b6b8cf`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/epoch_loop.sh` — `8eb5345c73024256e950b92f1a5c00ee2c2b297f34c425a66441a3d28ef09d89`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/epoch_run.sh` — `f94d4aed7ca6371ac28419e0bf9decc22a5b60cba158ae255a125f2d57f3cb68`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/render_running.py` — `c96201246d3ffe41622c97456a289d545d5b5a9c5ce83ea9ee44b24ea58fed49`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-running-table.md` — `ac92b77744b4778d70ddb8879b010969fa7652641f28436cf146739df3f65d04`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/paddle-running-refusals.json` — `1cc19fc7ab8ce7d83daec870b7ce002ecf77337a4958c4cb3fd0646078deee1b`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/odl-legacy-completed-inventory-20261030.md` — `f2db5e2be677e32e67171da2a5e91b04fb4040e38ff418f41164c783694a1ba9`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/odl-legacy-completed-inventory-20261030.json` — `500917d30e6eedf0381f81b9958b0e8446a47d9522b801cfd1c96081f365815f`
- `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030/odl-new-shards-strict-audit-20261030-v2.json` — `ad288381cd679944e56058cb389deb29b47454f35b2e21aaae8c821e2e0334b9`
