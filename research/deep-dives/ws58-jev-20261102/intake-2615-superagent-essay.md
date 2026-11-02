# Essay dive (2026-11-02)

| Claim | Verdict | Quote | Locator | sha256 |
|---|---|---|---|---|
| Four properties | CONFIRMED | Continuous: Users can interact with it directly | art:b12-15 (S1) | 5f92dce586ffbd8e8562aeba6e524d3b1d0d43726cbdba0110561aa2a264249c |
| Router no Bash, lighter model | CONFIRMED | it can run without a Bash tool at all | art:b30 (S2.1) | 10fdb457f77d5cfddc61a4c192f7c4f59f6e060e42615397923b0ba46b947bc4 |
| Lighter model | CONFIRMED | a lighter model can usually provide both speed and quality | art:b31 | b522048ef8a396ad7ddb1d76b2463fe1d9cc1a2acefae6365936676033774366 |
| Workers strongest, never talk to users | CONFIRMED | Workers never interact with humans directly. | art:b39 (S2.2) | ec62c8c3cb8ae03369b4d6ce0d3c540b63f2cfe5cfda0dac6bbb8ea71d6cd0e0 |
| Workers most capable models | CONFIRMED | they usually need the most capable models | art:b38 | 11c4b5afc63456d151ddcff3dffee151e9b3e13d24571fdf88b85534790705ed |
| Router batching | CONFIRMED | the larger the backlog, the lower the amortized inference time per decision | art:b34 | ae1e9a53136b1610f4f6afb8491c23b293dfc7fe5dc6dd76bb377fadbe6e8aea |
| Fast/Slow filter | CONFIRMED | We use two-stage filtering that combines programmatic policies with a large model | art:b47 (S3.1) | c84715a08664e059d189ddc787c7e3c83dd7232e5101b15e5b3fd13e18f2fcb2 |
| Fast path rules | CONFIRMED | such as the event source, the group, and user or bot allowlists | art:b48 | 4487267b59a98f7318929957f2d660c8794c8c6323d365247980215cfb44d337 |
| Thread | CONFIRMED | form an event stream, which we call a Thread | art:b53 (S3.2) | 32e8bbd84fd092944db5a29633c3f4d628278f926f55153f3fd86824425d4240 |
| Subscription pass-through | CONFIRMED | Code passes follow-up events in the Thread straight through to the subscribed Worker | art:b56 | f28c07b7f8198158b6f48e2c0923eb0442256f02847bf67c47908d5bdda2664e |
| Router only cold starts | CONFIRMED | The Router layer handles only cold starts of new tasks and cross-task coordination | art:b52 | ef679bbf99783ac48a358ed708eda9e8be812b715dedea08c3b23c35394fa637 |
| Many-to-many | CONFIRMED | Subscriptions between Threads and Workers are many-to-many. | art:b59 | ff7487ba2f0c27f223d5c3eb2d458ce42320e3d507406d94e03f893ded75d39c |
| Inline/Spill | CONFIRMED | Spill keeps full information outside the window | art:b62 (S3.3) | fcc806fa04a240e87fc0e22c43b4a6ef5fc1506ccf743924f06e05f815bd7dc8 |
| Chain of Recall | CONFIRMED | Chain of Recall | art:b67-69 | 9c598a34ee88ece9a1d839f62f4ff9563e823c183edbc3a615d9a74c11d6287d |
| IDs of related objects | CONFIRMED | inlines the IDs of closely related objects when it injects one | art:b69 | 13fc8b75f994e0804e0b8a02ee74908e1f1ae9e812382d23e3d51b2469a9e0e9 |
| Speculative execution | CONFIRMED | Results that turn out to be useful are delivered, and the rest are discarded. | art:b72 (S3.4) | 96303bb0ccc2921a65627d52c41fd39827fce5fa780188c3240ca4ef48c9fa14 |
| Full-duplex start/stop | CONFIRMED | A call to start() returns "Started" immediately | art:b80 (S4.1) | 0007637a2920bd30a91e46b99ac7940f20530d67a5f2e7be6a8d8c96ebfcab57 |
| Full-duplex not default | PARTIAL-NOTE | but it is not yet enabled by default | art:b82 (summary omits) | 283151a93f77080a97cfa4aeb80403ba48b8a7f93362846f898c9ef462965fad |
| 100-word cap | CONFIRMED | a cap of 100 words per reply | art:b86 (S4.2) | 3027804d5aa29367bf329ea45914007591b1047ec34cbc28817ce83eb714dd0b |
| Stateless cloud containers + DB | CONFIRMED | keeps sessions and other persistent state in a database | art:b91 (S5.1) | 5340cff15813a29dad5d2cceb4b6778436d335d0f2580256a08e85bfc9d7e806 |
| Daemon per endpoint, BYOM | CONFIRMED | Each endpoint needs only a lightweight daemon | art:b95; BYOM b96 | d60b2fec77a86b43a77156b3f852f254491dcc618c7b07a41f24f437808ffce2 |
| Watchdog | CONFIRMED | an independent Watchdog Session that runs outside the main system and is driven by scheduled messages | art:b102 (S6) | acdc63251e5c245d3544015366f03a0ded636ed1ba21133d4e83920ac939346a |
| Watchdog drift/loops | CONFIRMED | the model is stuck in an unproductive loop or has drifted from its goal | art:b101 | c852176aa0ea4ac24fc2074e863e05e75c0e09e18bdeccd28ea5d6ecdc4dce27 |
| Watchdog NL instructions | CONFIRMED | maintainers can ask it in natural language why something failed | art:b103 | 0da329a8c441b6293d7d61c71dfb47a26b79dd7486ca6b338dfc571cb85335d0 |
| Ablation setup | CONFIRMED | Each run had about 300 messages, of which about 20 were work requests. | art:b107 (S7.1) | 2889111d1e2105472c75c01ee0590566527a42100d3a9c5099f2b01f86af9c2d |
| 5 runs | CONFIRMED | Each design was run 5 times. | art:b107 | 9174235a1e2cd9acc21b357b2edb6dea7a11332016a5f1d06eb045b63981c521 |
| 12.4/15.7 | CONFIRMED | 12.4 minutes at p50 and 15.7 minutes at p95 | art:b114 | 52bec7f65e03f20fd76366588301a8a425d0f6302619fe3b1f98d5dc7a0c7368 |
| 29.5 p95 neutral, never delegated | CONFIRMED | With the neutral prompt, the model did not call a subagent in any of the 5 runs. | art:b114; p95 29.5 same block | f8e61f9fb1f769ebea170ca4144b4653bf4c159ec75c565b9f7c6dd4ec60261e |
| p95 29.5 | CONFIRMED | p95 reached 29.5 minutes | art:b114 | 887c601bc3a4bd43101779ac5effa41ca17f8e556f5ec320939d7966e628f4db |
| No-passthrough +30% | CONFIRMED | its Router makes about 30% more decisions per run | art:b115 | c48fed160bc82be99b59a5126eddfb1f2e6f9c6e4f4b418ecaaa3ed305409b00 |
| Cache read 23.2M->31.8M | CONFIRMED | total cache-read tokens rise from 23.2M to 31.8M, about 37% more | art:b115 | 37e24ba21a8ec39e5fc21b117fb9e3d4c336b1a12b6fcf067695a570006b3d97 |
| Stress 1->40, batch 1.0->2.8 | CONFIRMED | the average batch size increases from 1.0 to 2.8 | art:b119 (S7.2) | 805274787c679f9ed268bf71244fe3b9d104f3579415f6000489232bb26905e6 |
| 2.5s->3.9s | CONFIRMED | The time per request grows only from 2.5 s to 3.9 s | art:b119 | 49d0e6abd2bad8846d1e4c424ea7ba7e1fa234bdb5fd227e42a25485fba8453b |
| 6.4s->1.6s | CONFIRMED | falls from 6.4 s to 1.6 s | art:b119 | 62a53d1956edc9372918838efa7555e83cce6380edd8cdf4ee03f82c8cc05577 |
| Open problems | CONFIRMED | long-term memory becomes the main bottleneck | art:b124 (S8.1); sharding b123; security b133-135; W2W b123 | 797ffce4d6965fcf0b6507ad6d220bf2ac451232e94060ff2ba73ebc626d6c8c |
| Caveat synthetic | EXTRA | the results below are indicative only | art:b105 | 7d4956d926967df90d6fe82d383ac946815392f641cc68a5029d9d0cf5252105 |
| Anti-churn: new session per event | EXTRA-AGAINST-CHURN | Giving every event its own new session reverses the trade-off. | art:b23 (S2) | 8eb161cae9085866199885710d52881ee5d4290bf04b12482d73672d301d51f7 |
| Anti-churn: lost shared context | EXTRA-AGAINST-CHURN | the lack of a shared global context leaves their results disconnected | art:b23 | a162a12ecfcf4374796cf3e5263242f96756c4f3521b6533f8f4d5155bee8565 |
| Anti-churn: Router recover | EXTRA | the Router layer still has to recover that task's context | art:b67 | 367fa7a7c09db6e469f5cc2d09dfd0a4af87185e53287b0b7f38adb821b1c301 |
| Anthropic: bootstrap cost | EXTRA-AGAINST-CHURN | every session paid the full container setup cost up front. | anth: Many brains section | fced8787336814d2d638dd9afbff39305a22b1071752c84f9f4d6cf7f4a8e25e |
| Anthropic: TTFT | EXTRA | our p50 TTFT dropped roughly 60% and p95 dropped over 90% | anth: Many brains | 840d91bc6c910ee572464eed2b3967bc2cc3779d89f15cb633da9759d1ded0d8 |

## Sources
- X post https://x.com/DeepSeekHarness/status/2116857257245987236 (2026-11-01) is only a t.co link to X article the X Article linked from https://x.com/DeepSeekHarness/status/2116857257245987236, title "Exploring Super-agent Design: Towards a More Autonomous Agent System" (machine translation). Full text via api.fxtwitter.com saved as article.json/article.txt. syndication API returns same stub.
- Chinese original: NOT located (WebSearch and Bing found nothing). Unreachable/unverified.
- Repo https://github.com/deepseek-ai/dsh-superagent-prototype reachable (README states some article designs are future directions, not implemented; MIT; 7.1k stars).
- Anthropic: https://www.anthropic.com/engineering/managed-agents (308 -> https://www.anthropic.com/research/managed-agents), title "Scaling Managed Agents with stable interfaces", section "Decoupling the brain from the hands". Saved anth.html/anth.txt.
