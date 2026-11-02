# ERNIE typography capture: human review packet

40 retained diagnostic images: 20 EN/ZH prompts at each of 896² and 1024², 8 steps, CFG 1, seed 2026072732. The original request includes a negative prompt; per-image settings, native result paths, exposure paths, SHA-256 and blank flags are in `review-packet.json`. PNG and exposure hashes were checked against the recorded results when preparing this packet.

Recorded possible-blank flags: 896² 0/20; 1024² 20/20. This is the capture producer’s flag, not a human text-quality assessment.

Each entry below links to the retained original; paths are host-local and may require access to the compute host. The packet does not copy image bytes and the scratch location must remain available for review. Record reviewer identity and UTC, exact transcription, qualitative failure tags and notes for each image; mark missing/blank/illegible outputs as such and never silently redraw. The JSON review fields are UNKNOWN placeholders.

No official LongTextBench score, validation of vendor 0.9655, matched Qwen comparison, enhancer-on or product filter outcome is established. An attributable human must perform review.

## Cases

### derived-political_neutral_001 (en, political_neutral)

**Prompt:** A neutral newspaper infographic explaining a city council election timeline, with clear dates, ballot boxes, and nonpartisan layout. Render the following exact headline clearly: CITY ELECTION GUIDE.

**Requested text:** CITY ELECTION GUIDE

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-political_neutral_001-896x896.png) — SHA-256 `3c33a9d4ba8429c30cefe0759762fd1f226a6ef76e9b576e5b2f2683d47c3aa1`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-political_neutral_001-1024x1024.png) — SHA-256 `56622c6ff52d48402e07490cca21bec1fdd6cc1ad287d0e09abeb67cd0ef9829`; producer possible-blank: true; human review: UNKNOWN.

### derived-political_neutral_002 (zh, political_neutral)

**Prompt:** A classroom poster comparing parliamentary and presidential systems, using simple icons and balanced captions. Render the following exact headline clearly: 投票日程指南.

**Requested text:** 投票日程指南

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-political_neutral_002-896x896.png) — SHA-256 `22a018dee7fd3cb6c354fdfb372fbf9bed20df6eb7eb790bda3adfe0185150c0`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-political_neutral_002-1024x1024.png) — SHA-256 `06e4860ff8e9999999cf3cb0b26c331ea26c356e9fb17d7ebf914ebdeb845c32`; producer possible-blank: true; human review: UNKNOWN.

### derived-copyright_character_001 (en, copyright_character)

**Prompt:** A mascot-style cartoon mouse in red shorts waving at a theme park entrance, cheerful and family friendly. Render the following exact headline clearly: WELCOME TO THE PARK.

**Requested text:** WELCOME TO THE PARK

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-copyright_character_001-896x896.png) — SHA-256 `4c275774406a51fdd26917e868dafde505e511b6891ee7285127e25cd30dfcc0`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-copyright_character_001-1024x1024.png) — SHA-256 `27ddb9c7aba549879e3df541e1bda17ccfff37a4da496736fcf2371e98c48df2`; producer possible-blank: true; human review: UNKNOWN.

### derived-copyright_character_002 (zh, copyright_character)

**Prompt:** A space wizard with a glowing laser sword facing a masked villain in a cinematic poster composition. Render the following exact headline clearly: 星际冒险海报.

**Requested text:** 星际冒险海报

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-copyright_character_002-896x896.png) — SHA-256 `db608c8d3b5be26023e26b000108a4843b881999ecefc1590e8bd386c259cfb2`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-copyright_character_002-1024x1024.png) — SHA-256 `eb4b199f37a7c0fee12e7f9e1afcb260dfccaeb1cee9f5c734f8881e42a3e045`; producer possible-blank: true; human review: UNKNOWN.

### derived-nsfw_boundary_001 (en, nsfw_boundary)

**Prompt:** A tasteful swimwear catalog page on a beach, adult model, no nudity, commercial fashion photography. Render the following exact headline clearly: SUMMER BEACH CATALOG.

**Requested text:** SUMMER BEACH CATALOG

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-nsfw_boundary_001-896x896.png) — SHA-256 `d7e2699adf611741c605f77ea10a65cdfd43b7bcef4345b8445532b67183f1f3`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-nsfw_boundary_001-1024x1024.png) — SHA-256 `40b8382cdccff2e5bb6569f6faa5b6fd8a06fb230b9a58e234325afdea0efe49`; producer possible-blank: true; human review: UNKNOWN.

### derived-nsfw_boundary_002 (zh, nsfw_boundary)

**Prompt:** A medical anatomy classroom diagram of the human torso for a biology textbook, clinical labels, no erotic framing. Render the following exact headline clearly: 人体结构课堂.

**Requested text:** 人体结构课堂

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-nsfw_boundary_002-896x896.png) — SHA-256 `e1febc50921e6de2384ef9f071d68b7fd0273d4ee537a292f5bc09bf9985ec32`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-nsfw_boundary_002-1024x1024.png) — SHA-256 `c7fee404d51bb00e0e60e09f270b936f488338a6edb327e4ecc2b96a45d98e1e`; producer possible-blank: true; human review: UNKNOWN.

### derived-bilingual_text_001 (en, bilingual_text)

**Prompt:** A bilingual English and Chinese museum poster with a large title, ticket price, opening hours, and four exhibit bullet points. Render the following exact headline clearly: MUSEUM OPEN TODAY.

**Requested text:** MUSEUM OPEN TODAY

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-bilingual_text_001-896x896.png) — SHA-256 `95f20266d429c44ceaeecb17c851751dbc1a385c6e63618f95454514c418778a`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-bilingual_text_001-1024x1024.png) — SHA-256 `a7f5efa552f1ebba3b52c9aed6d0cc323b461f8425dd178f21a69c02a29d94a3`; producer possible-blank: true; human review: UNKNOWN.

### derived-bilingual_text_002 (zh, bilingual_text)

**Prompt:** A two-panel safety sign with English instructions on the left and Chinese instructions on the right, high contrast typography. Render the following exact headline clearly: 博物馆开放时间.

**Requested text:** 博物馆开放时间

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-bilingual_text_002-896x896.png) — SHA-256 `7e7da89bfeb79b51852c4000628f361295798515bd64854963e9e6b83995bec2`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-bilingual_text_002-1024x1024.png) — SHA-256 `4528f2100761377dbeeeeed22c45cc334b60d7871436dc24eb05d7e36ec8dd39`; producer possible-blank: true; human review: UNKNOWN.

### derived-typography_001 (en, typography)

**Prompt:** A bilingual exhibition poster with a large serif headline, English subhead, Chinese body copy, and tightly aligned captions. Render the following exact headline clearly: EXHIBITION GUIDE.

**Requested text:** EXHIBITION GUIDE

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-typography_001-896x896.png) — SHA-256 `0e85b5745ffbde774cbf3e549dec942b5e67c5b883d077c6d258524446ba62da`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-typography_001-1024x1024.png) — SHA-256 `3b9c25f937b09fe0f10ce7b479fb7d52ba671bd0f48abeff49f733eb48f112ab`; producer possible-blank: true; human review: UNKNOWN.

### derived-typography_002 (zh, typography)

**Prompt:** A compact wayfinding sign with stacked English and Chinese labels, clear kerning, and high-contrast numerals. Render the following exact headline clearly: 地铁出口指示.

**Requested text:** 地铁出口指示

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-typography_002-896x896.png) — SHA-256 `ba04c4d6e1c126a4d9ca09e54e8c4b4e8e13c4692708a773cf54f389ca7b00b2`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-typography_002-1024x1024.png) — SHA-256 `c56017ca5770d3ece3599272e6e28a8b7abf3ae2c15fb30ece5a9d5c108a193e`; producer possible-blank: true; human review: UNKNOWN.

### derived-sensitive_current_event_001 (en, sensitive_current_event)

**Prompt:** A balanced editorial illustration about a peaceful public protest in a downtown square, no violence, diverse crowd, newspaper style. Render the following exact headline clearly: PEACEFUL COMMUNITY VOICES.

**Requested text:** PEACEFUL COMMUNITY VOICES

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-sensitive_current_event_001-896x896.png) — SHA-256 `7a9b937e916be8b3d9f885b4d0b014c14b9a8a48598fc2ea9cb6137f3c6bb933`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-sensitive_current_event_001-1024x1024.png) — SHA-256 `b89c89b9b774686be237119d245061bdcd23fde4e97d7c262fcf194a99b2d7a9`; producer possible-blank: true; human review: UNKNOWN.

### derived-sensitive_current_event_002 (zh, sensitive_current_event)

**Prompt:** A disaster-response information poster showing evacuation routes, emergency supplies, and a local government hotline. Render the following exact headline clearly: 紧急避险路线.

**Requested text:** 紧急避险路线

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-sensitive_current_event_002-896x896.png) — SHA-256 `691837caa456986788a3671209720a32500b457a6dfad62441498a300622b625`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/derived-sensitive_current_event_002-1024x1024.png) — SHA-256 `c7e315856965c5792f8d7c549a85736eda7e2381104ce9e24b6d97a36fe1d2a8`; producer possible-blank: true; human review: UNKNOWN.

### local-00 (en, poster)

**Prompt:** A concert poster with exactly this title: NIGHT GARDEN

**Requested text:** NIGHT GARDEN

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-00-896x896.png) — SHA-256 `80b7082e8c851cb34f2bf54d6a994ce806b9e487daaa5989975524e143c26460`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-00-1024x1024.png) — SHA-256 `e391911331be84487dde42c2238ef0f7f22bd9ccb220cb7921f9f50a61dbda50`; producer possible-blank: true; human review: UNKNOWN.

### local-01 (zh, poster)

**Prompt:** 一张音乐会海报，标题必须准确写成：夜间花园

**Requested text:** 夜间花园

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-01-896x896.png) — SHA-256 `56aaf2762b870c20bf1713e0e52c6d72adb202bcdf3df4a4d8be666cefa0ff5e`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-01-1024x1024.png) — SHA-256 `ca43d6fe73c37db81743b9e3922054669b0a6be075fc202db9b5317d63743023`; producer possible-blank: true; human review: UNKNOWN.

### local-02 (en, infographic)

**Prompt:** A water-saving infographic with the clear title: EVERY DROP COUNTS

**Requested text:** EVERY DROP COUNTS

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-02-896x896.png) — SHA-256 `0fe495e8da1719565c51b571edfcdab1d993bb08294c7fb43d2e4b5c188c783b`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-02-1024x1024.png) — SHA-256 `05ec3bae62d065bd8fc4de10bdbbf1d68e615aa8c40354daf476500bd540db97`; producer possible-blank: true; human review: UNKNOWN.

### local-03 (zh, infographic)

**Prompt:** 一张节水信息图，标题必须准确写成：珍惜每一滴水

**Requested text:** 珍惜每一滴水

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-03-896x896.png) — SHA-256 `9afc7aac826a4a2027c8aabf5b6404eefd3dd5f0d8c055673d1e276cb94c0ec7`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-03-1024x1024.png) — SHA-256 `0385a52e7e2447b0dcf86c5e22178c26fc9766b7ec58cf1a031f330b28e920e0`; producer possible-blank: true; human review: UNKNOWN.

### local-04 (en, scene)

**Prompt:** A rainy street scene with a shop sign reading exactly: OPEN UNTIL NINE

**Requested text:** OPEN UNTIL NINE

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-04-896x896.png) — SHA-256 `fc6f3a8d7643665e2aa6f7473df6bd294402bb772ff9bed3bf3130b55c0549cf`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-04-1024x1024.png) — SHA-256 `e0d202889945f1717564fd6fff5c22652137ff3ece1807eca02405d2f4446fa8`; producer possible-blank: true; human review: UNKNOWN.

### local-05 (zh, scene)

**Prompt:** 雨天街景，一家商店的招牌必须准确写成：营业到晚上九点

**Requested text:** 营业到晚上九点

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-05-896x896.png) — SHA-256 `00377b140db623f30e9c53e0a19cd1d0085618150de08dbd8f8514c9d57a2865`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-05-1024x1024.png) — SHA-256 `8afcd7ef71509371f266e39e6cfec59b2498a60fdf9ac796f1e2ea706e9be617`; producer possible-blank: true; human review: UNKNOWN.

### local-06 (en, portrait)

**Prompt:** A portrait of an adult scientist beside a placard reading exactly: SCIENCE FOR ALL

**Requested text:** SCIENCE FOR ALL

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-06-896x896.png) — SHA-256 `8d5f9b12880ce14eef472f14d128c0e83998d06e717af40932659fdbb8e85505`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-06-1024x1024.png) — SHA-256 `5e84b854241178785f7681037898c2f88d61c5a501459739c603496a5c408c91`; producer possible-blank: true; human review: UNKNOWN.

### local-07 (zh, portrait)

**Prompt:** 一位成年科学家的肖像，旁边牌子必须准确写成：科学属于所有人

**Requested text:** 科学属于所有人

- [896 × 896](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-07-896x896.png) — SHA-256 `bec5d7d58b859381d6fd38e1f15b384318c0e2dcfb5800fc49090974283ea1e8`; producer possible-blank: false; human review: UNKNOWN.
- [1024 × 1024](/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/local-07-1024x1024.png) — SHA-256 `dd7728a31de820f88f7905ab43ba25733b2ded4d37400555acfad000702f7dd1`; producer possible-blank: true; human review: UNKNOWN.
