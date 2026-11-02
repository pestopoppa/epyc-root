# AK-WM fresh prefill preparation: refused

The manifest is an attempted bootstrap input, not a runnable or validated campaign. On 2026-11-02,
`prepare_iqk_matched_pair` refused it before creating either arm: the calibration bundle binds frozen
v9 `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, while current research campaign code requires v10
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. Do not relabel or reuse the v9 calibration as v10.
A fresh, identity-bound v10 calibration and reviewed experiment inputs are needed. No inference
was executed and no performance claim is made.
