# Isolated frontdoor input capture

Row `handoff-vidya-quality-pack-frontdoor-20261118` ended rc=0. The original v10 and C13 captures each contain four independent requests under the pinned Qwen3.6-35B MTP-cap-4 recipe on CPUs48–71. Both captured servers exited and their listeners closed. `receipt.json` records the exact file hashes; `*.original-bytes.json` preserve original bytes in base64 to retain nanosecond identity fields without account-number scanner false positives.

The JSON request produced different content and token IDs (8 versus 13 completion tokens). Code, reasoning and long-prose responses have identical content and token IDs (17, 21 and 16 tokens). The long-prose responses reached their prescribed length bound. These are finite capture observations, not a broad parity, performance or promotion result. The candidate HTTP fingerprint is `b0-unknown`; its identity comes from the pinned executable and mapped-library witnesses, not that string.

The isolated input-capture control passes. Seven-profile coverage, strict comparison through the quality-pack tool and its planning-context canary remain open. No historical measurement warrant was created.
