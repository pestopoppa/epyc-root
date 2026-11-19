# KPF-18 group-3 custody integration preparation

This lane-owned successor integrates the retained native manifest with `rebind_manifest.py` at preparation and `verify_manifest.py` at its entry. It preserves an exact copy of NI’s disabled launcher as `/mnt/raid0/llm/tmp/kvfork/g3-integrated-prep-20261104/predecessor-launch.sh.disabled`; NI’s packet and its source files were not modified. The successor never dispatches that launcher or any model command.

The actual 52-entry retained inventory passed exact-byte rebinding and the new entry’s `custody-check`. Default/official and `normal` entry both verified custody and then refused with rc78. Source/tool, inventory, mapping, retained launcher and manifest hashes are sealed before entry; the upstream original manifest SHA-256 is `50e1499b9a82fc83a7cdcb1415d543598915217cb9aef1798ce3270815763f4e`, and disabled launcher SHA-256 is `b6c5f22784322e8784c39712d77bcd723ab00bd7f0559f5dc0bfaedc6fce5a6c`.

The complete custody suite passes 21 model-free tests, including six integration controls covering real entry execution, native mutation, sealed packet mutation, pin/destination refusal, incomplete preparation and equal-byte relocation. No model weights were hashed, inference started or row published.

This is CUSTODY_ONLY_NOT_READY, not runnable GPU preparation. The historical lock helpers remain byte evidence only. Current lock semantics, independent validation-manifest custody, cancellation, whole-attempt supervision and GPU qualification still require implementation/qualification by the runtime owner. Preserve the original 150+64 GiB disk admission floor: the owner reports only 165 GiB available, below 214 GiB. Root GitNexus status is unindexed and impact cannot resolve this lane, so no graph-verified blast radius is claimed; the added entry has no runtime dispatch.

The generated successor is scratch at `/mnt/raid0/llm/tmp/kvfork/g3-integrated-prep-20261104`; no generated packet is stored in this report. Recheck with `bash /mnt/raid0/llm/tmp/kvfork/g3-integrated-prep-20261104/launch.sh custody-check`. Any missing/drifted scratch dependency refuses; a custody pass never means READY. The original R15 INVALID and all prior exposures remain unchanged.

Moved-packet content pins (SHA-256):

- `launch.sh`: `57037bd42341a572a807099a0f064eb4ca090e5f569a6cf14099d7203880804e`
- `SUCCESSOR-SOURCES.sha256`: `5eebb8ffac7882157af54f113992a35cedb67b03fc7641d4199c0f8c24071f7c`
- `NATIVE-SOURCES.sha256`: `a6c67a712fc36568e2f4120c90a623f5817becdbe7f083c38cdd0323f9d9c032`
- `expected-paths.json`: `44feb1cdf99a1a0299f2e5cf358e7331974d3aff3a4fc436014d69704b5acd97`
- `rebinding.json`: `7bb9dc296dac7d871a3e33a9771cf3e9b080c81c243f456cb5da5a7176b896f3`
- `PREPARATION.json`: `19324420177fe55876e891278c3cdae2e68b00419d4bc929141edc3a0c710b03`
