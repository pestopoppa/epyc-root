# Paid-call accounting by alternative arm

40 unique terminal paid executions: eight implementation executions across six task IDs, plus32 assistance/review executions. No cross-arm sum is compared with one baseline.

| Case / condition | Mode / branch | Paid calls | Uncached input | Output (reasoning subset) | Sum CLI wall s | Native known gen / unknown receipts | Same-condition main CLI wall s |
|---|---|---:|---:|---:|---:|---|---:|
| DS41-W-66 / accurate-light-v2 | gpu-OFF-off-common-light / protocol-arm | 2 | 56214 | 1440 (80) | 46.027 | 14111 / 0 (+0 pending archives) | 54.218 |
| DS41-W-66 / accurate-light-v2 | gpu-OFF-off-common-light / supplemental-identity | 2 | 56214 | 1440 (80) | 46.027 | 15889 / 0 (+0 pending archives) | 54.218 |
| DS41-W-66 / accurate-light-v2 | gpu-ON-on-common-light / protocol-arm | 2 | 46051 | 1405 (40) | 47.994 | 23599 / 0 (+0 pending archives) | 54.218 |
| DS41-W-66 / detailed | cpu-OFF-off-recommended / protocol-arm | 0 | unknown | unknown (unknown) | unknown | 5663 / 1 (+0 pending archives) | 74.824 |
| DS41-W-66 / detailed | gpu-OFF-off-common-on-sampling / protocol-arm | 1 | 66024 | 2589 (330) | 392.634 | 16482 / 1 (+0 pending archives) | 74.824 |
| DS41-W-66 / detailed | gpu-OFF-off-recommended / protocol-arm | 0 | unknown | unknown (unknown) | unknown | 15573 / 1 (+0 pending archives) | 74.824 |
| DS41-W-66 / detailed | gpu-ON-on-coding / protocol-arm | 1 | 51575 | 2269 (209) | 403.553 | 26791 / 0 (+0 pending archives) | 74.824 |
| MM-5 / detailed | cpu-OFF-off-recommended / protocol-arm | 1 | 22411 | 1771 (62) | 47.861 | 23918 / 0 (+0 pending archives) | 140.117 |
| MM-5 / detailed | gpu-OFF-off-common-on-sampling / protocol-arm | 1 | 21864 | 1574 (45) | 57.464 | 17175 / 0 (+0 pending archives) | 140.117 |
| MM-5 / detailed | gpu-OFF-off-common-on-sampling / supplemental-mechanical | 1 | 21864 | 1574 (45) | 57.464 | 19362 / 0 (+0 pending archives) | 140.117 |
| MM-5 / detailed | gpu-ON-on-coding / protocol-arm | 1 | 26502 | 1910 (49) | 61.727 | 26886 / 0 (+0 pending archives) | 140.117 |
| NARIQ-LIBTRELLIS-MAP-1 / detailed | cpu-OFF-off-recommended / protocol-arm | 1 | 28867 | 841 (12) | 35.072 | 21812 / 0 (+0 pending archives) | 89.899 |
| NARIQ-LIBTRELLIS-MAP-1 / detailed | gpu-OFF-off-recommended / protocol-arm | 2 | 82998 | 2057 (27) | 200.153 | 28796 / 0 (+0 pending archives) | 89.899 |
| NARIQ-LIBTRELLIS-MAP-1 / detailed | gpu-OFF-on-coding / protocol-arm | 1 | 49071 | 746 (20) | 24.604 | 7329 / 0 (+0 pending archives) | 89.899 |
| NARIQ-LIBTRELLIS-MAP-1 / detailed | gpu-ON-on-coding / protocol-arm | 2 | 74623 | 2155 (57) | 202.432 | 40090 / 0 (+0 pending archives) | 89.899 |
| PAW-5 / detailed | cpu-OFF-off-recommended / protocol-arm | 0 | unknown | unknown (unknown) | unknown | 8549 / 1 (+0 pending archives) | 66.922 |
| PAW-5 / detailed | gpu-OFF-off-common-on-sampling / protocol-arm | 0 | unknown | unknown (unknown) | unknown | 4615 / 0 (+0 pending archives) | 66.922 |
| PAW-5 / detailed | gpu-OFF-off-recommended / clean-replay | 2 | 45577 | 2143 (22) | 64.083 | 17453 / 0 (+0 pending archives) | 66.922 |
| PAW-5 / detailed | gpu-OFF-off-recommended / historical-false-pin | 2 | 43966 | 1816 (15) | 175.079 | 22217 / 0 (+0 pending archives) | 66.922 |
| PAW-5 / detailed | gpu-ON-on-coding / protocol-arm | 2 | 51219 | 1921 (38) | 183.180 | 56397 / 0 (+0 pending archives) | 66.922 |
| PFXC-A3 / detailed | cpu-OFF-off-recommended / protocol-arm | 1 | 21880 | 742 (0) | 84.128 | 6757 / 0 (+0 pending archives) | 111.711 |
| PFXC-A3 / detailed | gpu-OFF-off-recommended / protocol-arm | 2 | 39788 | 1723 (47) | 112.959 | 15195 / 0 (+0 pending archives) | 111.711 |
| PFXC-A3 / detailed | gpu-OFF-on-coding / protocol-arm | 0 | unknown | unknown (unknown) | unknown | 6919 / 0 (+0 pending archives) | 111.711 |
| PFXC-A3 / detailed | gpu-ON-on-coding / protocol-arm | 2 | 39846 | 2079 (125) | 172.902 | 22440 / 0 (+0 pending archives) | 111.711 |
| PFXC-A3 / detailed | gpu-ON-on-coding / supplemental-mechanical | 2 | 39846 | 2079 (125) | 172.902 | 23111 / 0 (+0 pending archives) | 111.711 |
| TU-GR-1 / detailed | cpu-OFF-off-recommended / protocol-arm | 2 | 56826 | 2153 (222) | 61.917 | 18047 / 0 (+0 pending archives) | 191.404 |
| TU-GR-1 / detailed | gpu-OFF-off-common-on-sampling / protocol-arm | 1 | 14755 | 1128 (70) | 35.288 | 28895 / 0 (+0 pending archives) | 191.404 |
| TU-GR-1 / detailed | gpu-OFF-off-common-on-sampling / supplemental-autoci | 2 | 37217 | 2725 (314) | 85.021 | 41780 / 0 (+0 pending archives) | 191.404 |
| TU-GR-1 / detailed | gpu-ON-on-coding / protocol-arm | 2 | 35756 | 2296 (131) | 71.520 | 25576 / 0 (+0 pending archives) | 191.404 |

Historical failed light review and qualified fresh rerun costs both remain charged, as separate categories in ACCOUNTING.json. Common ancestors and paid guidance are referenced once within each alternative; alternatives must not be summed together.

CLI wall includes local tools and is not pure model service time or parallel batch elapsed. Reasoning is already included in output. Unisolated manager/setup/coordination/source-audit costs are neither zero nor included. Raw model advisories and owner source-registry records are retained separately; this table invents no final verdict.

Native wire figures retain partial/late receipts and unknown counters; known sums do not erase missing data. The withdrawn, unlaunched stale-causal light-v1 plan is not billed and is labelled separately.

Next: main use this per-alternative ledger alongside the qualified owner quality register.
