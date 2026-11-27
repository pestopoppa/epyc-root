# A3B performance evidence across serving epochs

Exploratory task observations across serving epochs. CPU and GPU were not compared as a benchmark.

TTFT, token counts and resource samples are observational. Missing values stay unknown.
Oracle verdicts and independent acceptance are separate.

| Epoch / attempt | Raw status | Review | Wall s | Streaming TTFT median s | Prefill / decode median tok/s | Generated known / unknown receipts | Cached input known | MTP accepted / proposed | Resource samples |
|---|---|---|---:|---:|---|---|---:|---|---:|
| cache-safe-01 / cpu-DS41-W-66-off-recommended | no_candidate | no_candidate_review_record | 2670.42715382576 | 27.0682 | 64.07470783031081 / 2.7572756701017136 | 3524 / 0 | 1848787 | 2171 / 2668 | 1328 |
| cache-safe-01 / cpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended | no_candidate | no_candidate_review_record | 2671.4304513931274 | 27.6817 | 9.55263349894288 / 2.7485698186314265 | 1478 / 0 | 415014 | 911 / 1110 | 1332 |
| cache-safe-01 / cpu-PAW-5-off-recommended | no_candidate | no_candidate_review_record | 2671.0444371700287 | 41.2321 | 34.94523435663324 / 1.4437548881923292 | 3302 / 1 | 259875 | 1863 / 2866 | 1332 |
| cache-safe-01 / cpu-PFXC-A3-off-recommended | no_candidate | no_candidate_review_record | 2671.2050471305847 | 76.512 | 76.2565205020815 / 1.911104231135879 | 2485 / 0 | 131876 | 1570 / 1810 | 1333 |
| cache-safe-01 / gpu-DS41-W-66-off-common-on-sampling | interrupted | accepted | 1810.8267385959625 | 10.60265 | 101.9186077863286 / 29.3803416796579 | 16482 / 1 | 5436264 | 10314 / 12240 | 886 |
| cache-safe-01 / gpu-DS41-W-66-off-recommended | interrupted | pending_independent_review | 1810.1787266731262 | 9.92175 | 5.5948323149570705 / 35.68501256070088 | 15573 / 1 | 10612783 | 9804 / 11364 | 887 |
| cache-safe-01 / gpu-DS41-W-66-on-coding | oracle_pass | accepted | 1656.9295177459717 | 5.69515 | 233.12639094420035 / 29.26322783774112 | 26791 / 0 | 1434773 | 15924 / 21694 | 813 |
| cache-safe-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended | oracle_fail | pending_independent_review | 953.7078845500946 | 7.86165 | 17.20217504110635 / 10.399591956580299 | 6666 / 0 | 320682 | 3699 / 5918 | 473 |
| cache-safe-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended-guidance-1 | oracle_fail | pending_independent_review | 681.5183322429657 | 6.80915 | 30.280578881808815 / 30.40472977861222 | 10725 / 0 | 874020 | 6975 / 7488 | 338 |
| cache-safe-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended-guidance-2 | oracle_pass | rejected | 1080.4543101787567 | 8.8825 | 18.396061325975733 / 21.62227972625594 | 11405 / 0 | 798049 | 7173 / 8448 | 538 |
| cache-safe-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-on-coding | oracle_fail | pending_independent_review | 913.9819707870483 | 5.51425 | 179.36513182554253 / 9.245131861296578 | 8634 / 0 | 218828 | 5014 / 7228 | 454 |
| cache-safe-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-on-coding-guidance-1 | oracle_pass | pending_independent_review | 172.43948578834534 | 6.97995 | 5.91877932365886 / 25.40739468880647 | 1436 / 0 | 133197 | 902 / 1064 | 83 |
| cache-safe-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-on-coding-guidance-2 | interrupted | rejected | 1801.558188676834 | 8.4125 | 13.301533799862462 / 6.259362065900364 | 30020 / 0 | 642933 | 18947 / 22130 | 898 |
| cache-safe-01 / gpu-PAW-5-off-common-on-sampling | oracle_fail | pending_independent_review | 575.1465623378754 | 5.8031 | 15.324303520228277 / 14.637835408198594 | 4615 / 0 | 533829 | 2749 / 3716 | 285 |
| cache-safe-01 / gpu-PAW-5-off-recommended | oracle_fail | pending_independent_review | 460.45085644721985 | 7.65625 | 18.806654597556935 / 15.931216824577902 | 4685 / 0 | 588145 | 2706 / 3938 | 226 |
| cache-safe-01 / gpu-PAW-5-off-recommended-guidance-1 | oracle_fail | pending_independent_review | 236.5894341468811 | 3.27205 | 45.105189932966994 / 34.023326532924926 | 4174 / 0 | 314653 | 2730 / 2878 | 116 |
| cache-safe-01 / gpu-PAW-5-off-recommended-guidance-2 | oracle_fail | rejected | 1495.9865612983704 | 10.06195 | 23.014754211966768 / 8.541158563933225 | 13358 / 0 | 1930630 | 8343 / 9992 | 742 |
| cache-safe-01 / gpu-PAW-5-on-coding | oracle_fail | pending_independent_review | 836.5894815921783 | 8.8369 | 49.96941275557414 / 9.54663438719971 | 6745 / 0 | 505562 | 4017 / 5440 | 415 |
| cache-safe-01 / gpu-PAW-5-on-coding-guidance-1 | oracle_fail | pending_independent_review | 760.6155066490173 | 12.1844 | 350.6847541448034 / 20.059546033023253 | 10951 / 0 | 283540 | 6902 / 8090 | 377 |
| cache-safe-01 / gpu-PAW-5-on-coding-guidance-2 | oracle_fail | rejected | 664.1113822460175 | 15.57555 | 602.5917649490416 / 72.0289005930737 | 38701 / 0 | 416584 | 24970 / 27449 | 328 |
| cache-safe-01 / gpu-PFXC-A3-off-recommended | oracle_fail | pending_independent_review | 871.2984821796417 | 4.4193 | 79.10920309412461 / 15.290237148022296 | 8713 / 0 | 270451 | 5426 / 6542 | 431 |
| cache-safe-01 / gpu-PFXC-A3-off-recommended-guidance-1 | oracle_pass | pending_independent_review | 118.19489479064941 | 4.75065 | 13.905546529178292 / 31.1663447054879 | 1618 / 0 | 119837 | 1049 / 1130 | 57 |
| cache-safe-01 / gpu-PFXC-A3-off-recommended-guidance-2 | oracle_pass | rejected | 317.2830560207367 | 7.1088 | 11.057488825466478 / 36.75973303154663 | 4864 / 0 | 412104 | 3128 / 3450 | 156 |
| cache-safe-01 / gpu-PFXC-A3-on-coding | oracle_fail | pending_independent_review | 853.9770867824554 | 6.9805 | 46.02150975194116 / 9.977712633867402 | 7244 / 0 | 281324 | 4515 / 5446 | 422 |
| cache-safe-01 / gpu-PFXC-A3-on-coding-guidance-1 | oracle_fail | pending_independent_review | 624.7039132118225 | 6.16995 | 11.555714890971014 / 31.999692918493935 | 8732 / 0 | 437714 | 5573 / 6306 | 309 |
| cache-safe-01 / gpu-PFXC-A3-on-coding-guidance-2 | oracle_fail | rejected | 270.73016834259033 | 3.7634 | 54.92591813568661 / 44.54175336602936 | 6464 / 0 | 842193 | 4165 / 4580 | 133 |
| cpu-02/measured-01 / cpu-DS41-W-66-off-recommended-numa-resume-1 | interrupted | no_candidate_review_record | 366.35620045661926 | None | None / None | None / 1 | None | None / None | 181 |
| cpu-02/measured-01 / cpu-MM-5-off-recommended | awaiting_source_review | rejected | 2858.9489142894745 | 6.131 | 85.52881543982323 / 6.027583508533285 | 12614 / 0 | 1032556 | 8048 / 9092 | 1414 |
| cpu-02/measured-01 / cpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended-numa-resume-1 | interrupted | no_candidate_review_record | 3226.565288543701 | 216.3524 | 82.00045101729394 / 4.215875776367298 | 9700 / 0 | 70935 | 5438 / 8518 | 1610 |
| cpu-02/measured-01 / cpu-PAW-5-off-recommended-numa-resume-1 | oracle_fail | rejected | 1157.219079732895 | 9.70895 | 20.293802362605902 / 7.003392718781855 | 5247 / 0 | 859875 | 3126 / 4222 | 576 |
| cpu-02/measured-01 / cpu-PFXC-A3-off-recommended-numa-resume-1 | oracle_pass | rejected | 1394.4652924537659 | 5.6144 | 20.11040612965179 / 4.569655840017098 | 4272 / 0 | 254252 | 2621 / 3294 | 694 |
| cpu-02/measured-01 / cpu-TU-GR-1-off-recommended | awaiting_source_review | pending_independent_review | 1617.8862564563751 | 14.4786 | 74.13695865601838 / 5.562720151219805 | 5488 / 0 | 390976 | 3342 / 4274 | 803 |
| legacy-boundary-v3/boundary-01 / cpu-DS41-W-66-off-recommended-numa-resume-1-boundary | oracle_pass | accepted | 992.7343094348907 | 9.0167 | 74.74638621015332 / 7.409320060215077 | 2139 / 0 | 764184 | 1363 / 1542 | 484 |
| legacy-boundary-v3/boundary-01 / cpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended-numa-resume-1-boundary | oracle_fail | pending_independent_review | 2140.46577835083 | 147.87325 | 48.53347446336334 / 24.234187625607497 | 10634 / 0 | 193986 | 5933 / 9394 | 1067 |
| legacy-boundary-v3/boundary-01 / gpu-MM-5-off-common-on-sampling | awaiting_source_review | rejected | 364.84355187416077 | 2.1559 | 405.32169805371495 / 40.023746246274854 | 8477 / 0 | 538648 | 5394 / 6134 | 169 |
| legacy-boundary-v3/boundary-01 / gpu-NARIQ-LIBTRELLIS-MAP-1-off-common-on-sampling-supplement | oracle_pass | pending_independent_review | 368.48154735565186 | 4.105 | 77.27688109192563 / 37.46357707784099 | 7329 / 0 | 402190 | 4392 / 5850 | 181 |
| legacy-boundary-v3/boundary-01 / gpu-PFXC-A3-off-common-on-sampling-supplement | oracle_fail | pending_independent_review | 330.80731678009033 | 2.16155 | 245.33286553157214 / 39.40814229867151 | 6919 / 0 | 328066 | 4357 / 5112 | 163 |
| legacy-boundary-v3/boundary-01 / gpu-PFXC-A3-on-coding-post-review-mechanical-3 | mechanical_harness_error | no_candidate_review_record | None | None | None / None | None / 0 | None | None / None | 0 |
| legacy-boundary-v3/boundary-01 / gpu-TU-GR-1-off-common-on-sampling | awaiting_source_review | rejected | 265.6879677772522 | 3.4337 | 333.9204768384409 / 41.741319410997875 | 6470 / 0 | 903264 | 4028 / 4852 | 127 |
| legacy-boundary-v3/boundary-01 / gpu-TU-GR-1-on-coding | awaiting_source_review | rejected | 543.250518321991 | 4.3564 | 630.5342576142432 / 35.96943015156125 | 13671 / 0 | 423863 | 8396 / 10526 | 263 |
| slot3-recovery/fix-01 / gpu-MM-5-on-coding | awaiting_source_review | rejected | 476.84097814559937 | 4.4268 | 203.69713805521033 / 42.02675187674662 | 12660 / 0 | 641588 | 8053 / 9178 | 228 |
| slot3-recovery/fix-01 / gpu-PFXC-A3-on-coding-post-review-mechanical-3 | oracle_fail | accepted | 101.60501265525818 | 6.6958 | 20.89789232293877 / 37.70185024472729 | 671 / 0 | 139633 | 424 / 488 | 48 |
| objective-followup/tu-01 / cpu-TU-GR-1-off-recommended-objective-1 | awaiting_source_review | pending_independent_review | 758.7315089702606 | 14.1355 | 185.56389576242958 / 9.189376207149875 | 3366 / 0 | 196019 | 2161 / 2404 | 376 |
| objective-followup/tu-01 / gpu-TU-GR-1-off-common-on-sampling-objective-1 | awaiting_source_review | rejected | 487.02503299713135 | 6.3454 | 118.15353450736721 / 51.937361153699534 | 12765 / 0 | 1205192 | 8147 / 9200 | 240 |
| mm-objective-followup/mm-01 / cpu-MM-5-off-recommended-objective-1 | awaiting_source_review | pending_independent_review | 788.9227292537689 | 4.284 | 56.73362818978142 / 13.79193561715374 | 5829 / 0 | 627129 | 3778 / 4094 | 383 |
| mm-objective-followup/mm-01 / gpu-MM-5-off-common-on-sampling-objective-1 | awaiting_source_review | pending | 182.37692403793335 | 6.5668 | 60.1414003754866 / 51.947480919495234 | 3666 / 0 | 387594 | 2336 / 2648 | 82 |
| persistent-callback/cpu-tu-mm-01 / cpu-MM-5-off-recommended-v4-objective-2 | awaiting_source_review | accepted | 1444.6521515846252 | 6.9311 | 48.863235912108976 / 6.269680461809429 | 5475 / 0 | 720532 | 3472 / 3992 | 701 |
| persistent-callback/cpu-tu-mm-01 / cpu-TU-GR-1-off-recommended-paid-2 | awaiting_source_review | rejected | 1704.9933912754059 | 9.72875 | 46.413751564271706 / 14.081252920499274 | 9193 / 0 | 832483 | 5896 / 6582 | 849 |
| persistent-callback/mm-v4-01 / gpu-MM-5-off-common-on-sampling-v4-objective-2 | awaiting_source_review | accepted | 585.9374752044678 | 7.85915 | 23.204141260624723 / 26.37324425425988 | 5032 / 0 | 315811 | 3175 / 3702 | 270 |
| persistent-callback/mm-v4-01 / gpu-MM-5-on-coding-v4-objective-1 | awaiting_source_review | accepted | 1134.5732131004333 | 6.0371 | 58.89734081310864 / 16.67782738719437 | 14226 / 0 | 849371 | 9099 / 10232 | 555 |
| persistent-callback/paw-clean-01 / gpu-PAW-5-off-recommended-clean-guidance-1 | oracle_fail | pending_independent_review | 237.72326183319092 | 4.379049999999999 | 576.4968759632405 / 36.312182106265894 | 2449 / 0 | 450677 | 1520 / 1844 | 117 |
| persistent-callback/tu-off-paid-01 / gpu-TU-GR-1-off-common-on-sampling-paid-2 | awaiting_source_review | pending_independent_review | 753.7409279346466 | 7.586 | 65.18637025426104 / 36.10339929208987 | 9660 / 0 | 1673054 | 6157 / 6972 | 369 |
| persistent-callback/tu-on-v2-01 / gpu-TU-GR-1-on-coding-v2-objective-1 | not_started | no_candidate_review_record | None | None | None / None | None / 0 | None | None / None | 0 |
| persistent-callback-admission-v2/paw-clean-paid-01 / gpu-PAW-5-off-recommended-clean-paid-2 | oracle_fail | rejected | 217.36617302894592 | 3.74735 | 258.8751008721969 / 102.52216457247361 | 10319 / 0 | 1689790 | 6373 / 7866 | 106 |
| persistent-callback-admission-v2/tu-on-paid-01 / gpu-TU-GR-1-on-coding-paid-2 | awaiting_source_review | rejected | 148.53783655166626 | 15.0179 | 15.968584570780491 / 116.8818554912248 | 2787 / 0 | 456810 | 1780 / 2004 | 72 |
| persistent-callback-admission-v2/tu-on-retry-01 / gpu-TU-GR-1-on-coding-v2-objective-1 | awaiting_source_review | pending_independent_review | 213.8635654449463 | 2.2539 | 163.49908570217457 / 112.40464437592043 | 9118 / 0 | 268162 | 5490 / 7248 | 104 |
| persistent-w66-light-12/light-01 / gpu-DS41-W-66-off-common-light-v2 | oracle_pass | rejected | 1141.6899876594543 | 6.51535 | 179.81246744896214 / 48.68081547029661 | 14111 / 0 | 4827393 | 8952 / 10242 | 548 |
| persistent-w66-light-12/light-01 / gpu-DS41-W-66-on-common-light-v2 | oracle_pass | accepted | 1518.752456188202 | 5.155150000000001 | 148.57253259617733 / 43.49559273751446 | 23599 / 0 | 5133330 | 14413 / 18302 | 747 |
| persistent-mm-mechanical/mechanical-01 / gpu-MM-5-off-common-on-sampling-v4-mechanical-3 | awaiting_source_review | pending_independent_review | 143.03752899169922 | 6.4172 | 108.61257599870736 / 23.87493865745803 | 2187 / 0 | 208919 | 1392 / 1582 | 65 |
| persistent-tu-off-auto-ci/auto-01 / gpu-TU-GR-1-off-common-on-sampling-auto-ci-1 | review | pending_independent_review | 179.99415707588196 | 3.2491 | 209.29855862639687 / 105.91594168382582 | 7777 / 0 | 728787 | 5019 / 5504 | 87 |
| persistent-tu-off-auto-ci/auto-01 / gpu-TU-GR-1-off-common-on-sampling-auto-ci-2 | review | rejected | 145.40196704864502 | 2.6495 | 190.56756277229806 / 79.78272777968782 | 5108 / 0 | 1067057 | 3191 / 3814 | 67 |
| persistent-w66-light-identity/identity-01 / gpu-DS41-W-66-off-common-light-v2-identity-1 | oracle_pass | accepted | 37.45286798477173 | 0.4335 | 220.2485504892271 / 132.7769813890931 | 1778 / 0 | 118557 | 1114 / 1326 | 11 |

## Qualification and accounting

- The CPU placement incident remains tagged on the original affected attempts. Their raw observations remain available.
- Continuations retain each parent phase and this phase separately. Cumulative counters use only hash-bound observed ancestry.
- Elapsed request intervals are unioned by recorded timestamps. Native prefill and decode phase envelopes are timing-derived estimates.
- Resource references index the serving epoch's samples during forwarded windows. Samples include overlapping slots and shared host activity.
- The adapter's upstream, delivered and client TTFT measures retain their distinct clocks. First-body and nonstream measurements supply no TTFT.
- Unreceipted archives, pre-forward rejections and missing counters are retained separately. A partial attempt is insufficient for a complete cost.
- Shared RAM cache settings do not remove ordinary in-slot reuse counters.

Independent acceptance records counted: 9.
Next: owner refresh at the next evidence boundary.
