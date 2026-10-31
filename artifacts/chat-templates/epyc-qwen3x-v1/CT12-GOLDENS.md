# CT-12.4 reconstructed template goldens

These seven request/render pairs are the CT-12.4 reconstruction of the CT-7
mechanism cases, not recovered August 2026 fixture files. CT-7 described its
cases but did not persist them. On 2026-10-21 CT-12.4 reconstructed them and
compared the patched and champion server renders to Jinja2. The retained run
script is `/mnt/raid0/llm/tmp/ct12-is-input-20261021/ct12_4_goldens_ab.sh`
(SHA-256 `0c58669d398811e39d46fbe26b2b729ee628f961e7ba7f8d88b97aeebde9586f`).
The extracted requests come from its `F` dictionary, and expected prompts from
`ct12-4/collect_A_epyc-qwen3x-v1.json` (SHA-256
`d9e52b69dcf0670f4379f142493a1acba4626cb83104f9ec0c20edc83db17e82`).
Each prompt equals the corresponding B render (file SHA-256
`ad395a97f018cfe0154a2f52e0a9ccce3c89d3cc774931663fd2807f4a2c4887`),
and the retained verdict records a Jinja golden match for all seven
(`ct12-4/verdict.json`, SHA-256
`25a3484c93d8c0a713f8a301619dd38422398a5677f4b06f6ddbc2a01d6bb89a`).
The source template is `chat_template.jinja` SHA-256
`faaecb215031c149c169e113800d69497b2dd9451602b82069d13aec651d8c15`.

With Python and Jinja2 installed, run:

```sh
python3 artifacts/chat-templates/epyc-qwen3x-v1/check_ct12_goldens.py
python3 artifacts/chat-templates/epyc-qwen3x-v1/check_ct12_goldens.py /path/to/candidate.jinja
```

The check reproduces CT-12.4's Jinja environment and compares UTF-8 rendered
bytes to the saved prompts. It models the server consuming top-level
`reasoning_effort` before template rendering. A candidate difference is reported
by fixture ID with a nonzero exit; it requires review. This is a render check,
not a server/tokenizer test or a quality evaluation. The original run's full
A/B included additional templates and injection cases; these files preserve
only its seven reconstructed CT-7 mechanism cases.
