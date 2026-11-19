# S8-c layout and partial-removal offline tests

These tests define behavior for an experimental candidate. They use synthetic in-memory cells, tensors and injected removal operations; they do not load a model, launch inference or modify a production kernel. The exact guard/helper interface must follow the implementation under review. A test-only adapter should expose its result, the occupied `(physical_cell, position, sequence_ids)` mapping, exact K/V bytes, prompt/checkpoint identity and calls to removal/position-shift operations. Take a full pre-call snapshot; compare post-call state with it where unchanged or restored state is required.

## Layout admission

Use a sequence with positions `0..7`, four sink positions, one cache stream and non-transposed K/V rows. Give every physical cell a distinct byte pattern and monotonically distinct score. Unless a case states otherwise, sequence 0 owns every occupied cell and the operation must validate the layout before scoring or mutation.

| Case | Fixture change | Required result |
|---|---|---|
| Dense identity | Physical cell i is logical position i, all rows valid. | Accepted. Scoring consumes each matching K/V row, excluding the protected sinks and recent reservation as specified. |
| Logical gap | Remove position 3 but retain positions 0..2 and 4..7. | Rejected before any tensor read or cache mutation by the conservative guard. |
| Physical permutation | Swap metadata positions of physical cells 2 and 3. | Rejected before tensor read or mutation even though logical positions are contiguous. |
| Wrong sequence | Cell 3 belongs only to sequence 1, while sequence 0 owns the rest. | Rejected before reading that cell or mutation. Check the original state of both sequences. |
| Extra shared owner | Cell 3 belongs to sequences 0 and 1. | Rejected if the implementation has not proved shared-cell rollback and isolation; neither sequence changes. |
| Transposed V | Same apparent 3-D tensor shape, but V uses transposed cache storage. | Rejected before row-wise V extraction unless the implementation has a separately tested correct transpose-aware extractor. |
| Cache alias | Backing KV cache is an alias whose `seq_rm` may return true without removing cells. | Rejected before mutation, or postcondition detects unchanged occupancy and invokes verified rollback/invalidation; never report the planned count as removed. |
| Hybrid / recurrent | Wrap attention cache with a recurrent memory object. | Rejected before mutation unless the candidate implements and tests whole-memory transactional support. |
| Multiple streams | Two cache streams, target sequence in the nonzero stream. | Rejected before extraction unless the row extraction explicitly binds the sequence's actual stream offset. |
| Beyond capacity | `pos_max >= cell_capacity`; also test a completely empty sequence and out-of-range/negative sequence ID. | Clean rejection with no out-of-bounds tensor access, assertion, or state mutation. Empty behavior must match documented API contract. |
| Unsupported tensor | Null K/V, missing dequantizer, unsupported row width or incompatible K/V tensor strides. | Clean rejection before any partial mutation; no out-of-range backend read. |
| Pending shift | Cell metadata has an unapplied position shift. | Reject or synchronize/resolve it under an explicit verified contract before deriving scores or positions. |

Each rejection checks **zero mutation calls**, unchanged K/V and cell metadata, unchanged prompt/checkpoint identity, and no foreign sequence data reads. Use a fake tensor backend that records row offsets to distinguish a genuinely pre-read guard from a late error.

## Reservation and eviction policy

Use recorded deterministic scores rather than invoking a model. Check exact removed logical positions, successful removal count, and preserved sink/recent positions. Cover `compression_ratio` 0 and 1, `n_sink` 0 and equal to occupied count, `keep_recent` 0 and larger than the available retained non-sink budget, and `recency_ratio` 0, 0.25 and 1.0. Reject negative counts, NaN/infinite/out-of-range ratios, and simultaneous positive absolute and ratio reservations before mutation. Compare every zero-recency case, including the 100%-compression boundary and tied scores, with the original algorithm: preserve its strict-threshold tie behavior and returned count. Confirm recent reservation is based on **retained budget**, not total input; sink and recent sets cannot overlap beyond existing occupied positions.

## Removal failures and state integrity

Construct at least two disjoint selected ranges, for example `[1,2)` and `[4,5)`, and an injectable removal implementation with call recording. The first failure test returns false on the first range and requires an error with a byte-for-byte unchanged full state. The second returns true for the first range and false for the second. It must not return success, continue to later ranges, shift positions, or report the planned removal count. The supported outcome is either:

1. a verified restoration of the full sequence, exact original positions, ownership, K/V bytes and prompt/checkpoint state, followed by an error; or
2. a distinct unrecoverable status which causes the server to invalidate the slot, clear its logical prompt and checkpoints, and prevent cache reuse before reporting an error.

If restoration is supported, inject both a failed state restore and a restore that reports success but yields a different state; both must take the invalidation path. If only a strictly proven non-failing direct-cache implementation is admitted, unit-test the extracted transaction/error handler with a fake backend and integration-test that every unsupported/failable backend is rejected **before** the first removal; do not claim that the real direct backend has been forced to fail.

For the proposed `llama_kv_compress_plan::occupied/select/remove` interface, make `remove` report both successfully removed count and `ok`. A known-unmutated first-range failure can map to `-1`; an earlier successful range followed by failure must map to `-2` and trigger server invalidation. A callback that changes state before returning false must also take the `-2` path unless the implementation can prove that backend's failed call is non-mutating. Exercise the real server's propagation with the test seam, not just the planner return value.

Verify `compact_positions=false` never shifts positions. For `compact_positions=true`, require all removals and occupancy postconditions to succeed before the first shift, and compare every shifted retained position with an independently computed contiguous mapping; when this transactional guarantee cannot be implemented, reject this mode before mutation.

## Lifecycle tests

After a successful non-compacting eviction creates gaps, issue a second operation: the conservative version must reject it cleanly and leave the post-first-call state untouched. A future gap-aware implementation instead needs an independent oracle that maps each occupied `(sequence, logical position)` to its **physical** K/V row and reserves the newest actual positions, not `pos_max + 1` positions. Test a cache with equal `pos_max` but different occupancy and physical order to ensure they do not select identical stale rows by accident.

Test server error propagation separately: ordinary preflight rejection must preserve the original slot, while an explicitly unrecoverable partial mutation must clear logical prompt and checkpoint state before any subsequent request; the server must never report the requested eviction count as a successful operation when any range failed. Confirm an empty or malformed request and a failed operation do not claim quality or throughput improvement.
