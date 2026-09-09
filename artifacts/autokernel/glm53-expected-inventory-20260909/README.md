# GLM six-shard expected inventory — metadata preparation only

This packet declares **expected** model file hashes from original cached remote
metadata. It does not attest that local model bytes were verified, does not
authenticate the remote service anew, and is not a model-preparation receipt,
resource grant, executable campaign config, profile, or scientific acceptance.

Original remote repository: `unsloth/GLM-5.3-Flash-GGUF`; revision
`d425e572fb9686125831f476129e51cea34bc5b4`.
Model root: `/mnt/raid0/llm/models/unsloth/GLM-5.3-Flash-GGUF/UD-Q4_K_XL`.
All six remote LFS SHA-256 values match the corresponding original download
metadata etags; tree size and LFS size agree. Declared total model bytes:
**199,707,321,347**. Authoring opened only the bounded cache JSON and six metadata
files; it never opened or stat'ed this declared model root or any member.

## Retained files and identity meanings

`model-identity.expected.json` uses the existing owning
`epyc.autokernel.model_identity.v1` grammar, with exactly six relative basename /
SHA-256 rows. Keep it outside the model directory, whose exact file inventory is
checked by the owning validator.

- Manifest byte SHA-256:
  `a9984ae6a18f7b25dd27086abd32b74056264a9cc64ba074067e8a8bb90be626`.
- Expected normalized inventory SHA-256:
  `21d760be3bd473865b31f3b3d9ca28b30a2f7bd12b71660e64191ff02ff11fcc`.
- Expected entry-file SHA-256 (shard 1, current serving model-digest convention):
  `00dceaf3ed08781b1e44513a44ebb19e96248d01ba2a80b17f675a2b6fa9a1ee`.

The normalized inventory digest hashes canonical JSON of model_path and sorted
path/SHA rows, not model payload. It must not be substituted for the entry-file
digest. The original `CaptureModelIdentity.validate()` must later verify all six
actual file hashes and exact inventory under the scheduled preparation/resource
owner. That real I/O/CPU work was not performed here. A metadata-only sidecar
cannot confer the validator's original issuance.

`source-tree.json.base64` is lossless standard base64 with one terminal newline;
decoding yields the original 14,118 bytes, which have no terminal newline. This
avoids changing original JSON bytes to fit a text patch. The six files
`download/00001.metadata` through `00006.metadata` are byte-exact source copies.
The sidecar records the tree encoding/path, encoded hash, decoded hash/size and
the original cache paths, byte
hashes, remote names, sizes, LFS identities, Git blob IDs, Xet IDs and etags. Its
explicit flags are `local_model_bytes_verified: false` and
`remote_metadata_freshly_authenticated: false`.
The original decoded source metadata totals 14,865 bytes; this is distinct from
the encoded retained-file sizes and from the declared model-payload total.

| Source copy | SHA-256 |
| --- | --- |
| source-tree.json.base64 (decoded bytes) | `4badb4fd6433a833d7ae7525732c865d7d73a7ace347f23e99c56a534e279ba1` |
| download/00001.metadata | `73a4dd31c2d5ed7eaf8916ef11441f32b54170e49860af10a0ca13576452c865` |
| download/00002.metadata | `c9dc0fe62c56980d9c77bcb7ff5ee374508b9793ef07f196edb4101a0caadc7a` |
| download/00003.metadata | `a69d0c55586fbda48a42f136a178afcfe616f0ce80a015d1129438106decd3d8` |
| download/00004.metadata | `762b18f94ef0afc8d8895fa83a7e19c18b16a95fa43ebe318fd2b2b20b520c2f` |
| download/00005.metadata | `1028738e8037b9e669f61a60a394b00f6ae1fb0780f70d5de860740b05842eee` |
| download/00006.metadata | `314aab244df25196616fadb8ad306920686d89c25c29f9dd9a28e19bc1a75ff4` |

## Reproducible author and tests

`author_expected_inventory.py` is a task-local author, not an installed runtime
service or new grading path. It accepts explicit cache/model/output paths,
requires a new output directory, and reads only bounded regular metadata files
with no-follow/nonblocking descriptor traversal. Source limits are 64 KiB for
the tree, 4 KiB per download metadata file, and 1 MiB for assembled output.
It refuses malformed or changed sources, mixed revisions, etag/hash/size
mismatches, duplicate or unsafe names, missing/extra selected shards, and
symlink/FIFO sources. Existing packets are never overwritten.

From this directory, with an explicitly selected research checkout:

```sh
EPYC_RESEARCH_ROOT=/absolute/path/to/epyc-inference-research TMPDIR=/mnt/raid0/llm/tmp python3 -m pytest -q test_expected_inventory.py
```

Without EPYC_RESEARCH_ROOT, only the owning-validator compatibility test skips;
all metadata-author tests remain runnable. With the published research source
selected, all 31 tests passed without skips. The owning test hashes **tiny
synthetic files only**, proves identical canonical normalization, and verifies
that changed tiny bytes are refused. The author test separately asserts that
model member paths are never opened. This is not a real six-shard verification.

No real ScheduledModelPreparation/config is generated here. Future use must bind
the actual original target/recipe/build/prompt and source identities before
selection. Original GLM prompt protocol, BIND/HELD, resource authorization and
qualified experimental build/enrollment gates remain unchanged. The published
independent_full_request_v1 CPU profile mode does not express the original GLM
token-array, cached prefill/decode, seed, or exact-token trajectory protocol.
