# Phase -1 Round 11 — NEW-DATA-DOMAIN BATCH

Mechanisms only testable after the data expansion: options vol
surface, liquidation cascades, mark-index basis, cross-venue
funding aggregates, on-chain stress/flow. Daily clock; signal day
d -> entry close d -> eval +k d; trailing-prior-day percentiles.
Column coverage differs per source (options 2021+, liq 2022-12+,
basis 2019+, funding agg, on-chain 2010+) — powered windows differ.
Universe: BTC harmony clock + 7 Binance perps. n_trials=46.

| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dvol_spike_bounce_1d | 139 | 0.540 | 0.457 | FAIL | 2216 | 0.25 | 0.706 | 0.000 | 0.260 | mixed | pass | **WATCH** |
  (power: n=139 (n_eff=139), Sharpe=0.25, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+17.3bp/ev t=0.59 long%=100% L=+17.3 S=+nan
  bb_p=0.317 (block=5)
  eras: 2022 n=32 net=+311 | 2023 n=29 net=+1406 | 2024 n=28 net=+2065 | 2025 n=28 net=-1388 | 2026 n=22 net=-179
  funding-carry adj: net=+1952bp (paid +264bp carry; 100% of events have funding coverage)
| skew_extreme_reversal_3d | 114 | 0.518 | 0.427 | FAIL | 2062 | 0.32 | 0.744 | 0.000 | 0.519 | mixed | pass | **WATCH** |
  (power: n=114 (n_eff=114), Sharpe=0.32, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+23.7bp/ev t=0.49 long%=60% L=+37.8 S=+2.9
  bb_p=0.312 (block=5)
  eras: 2022 n=29 net=-1087 | 2023 n=51 net=+4415 | 2024 n=8 net=-995 | 2025 n=22 net=-410 | 2026 n=4 net=+138
  funding-carry adj: net=+1748bp (paid +313bp carry; 100% of events have funding coverage)
| iv_term_inversion_3d | 150 | 0.487 | 0.408 | FAIL | 3635 | 0.39 | 0.807 | 0.000 | 0.450 | mixed | pass | **WATCH** |
  (power: n=150 (n_eff=150), Sharpe=0.39, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+17.5bp/ev t=0.36 long%=100% L=+17.5 S=+nan
  bb_p=0.299 (block=5)
  eras: 2021 n=23 net=-177 | 2022 n=41 net=+4279 | 2023 n=27 net=+3872 | 2024 n=25 net=+478 | 2025 n=26 net=-1769 | 2026 n=8 net=-3048
  funding-carry adj: net=+2522bp (paid +1113bp carry; 100% of events have funding coverage)
| liq_cascade_cont_1d | 143 | 0.434 | 0.355 | FAIL | -769 | -0.12 | 0.420 | 0.000 | 0.820 | mixed | pass | **KILL** |
  (power: n=143 (n_eff=143), Sharpe=-0.12, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+4.0bp/ev t=0.15 long%=52% L=+3.5 S=+4.6
  bb_p=0.314 (block=5)
  eras: 2023 n=10 net=+33 | 2024 n=59 net=-2143 | 2025 n=54 net=-1025 | 2026 n=20 net=+2365
  funding-carry adj: net=-807bp (paid +38bp carry; 100% of events have funding coverage)
| liq_flush_bounce_1d | 136 | 0.471 | 0.389 | FAIL | -425 | -0.08 | 0.443 | 0.000 | 0.812 | mixed | pass | **KILL** |
  (power: n=136 (n_eff=136), Sharpe=-0.08, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-6.3bp/ev t=-0.29 long%=100% L=-6.3 S=+nan
  bb_p=0.419 (block=5)
  eras: 2023 n=11 net=-381 | 2024 n=57 net=+893 | 2025 n=45 net=+1422 | 2026 n=23 net=-2358
  funding-carry adj: net=-767bp (paid +342bp carry; 100% of events have funding coverage)
| premium_basis_converge_1d | 1048 | 0.548 | 0.517 | PASS | 23350 | 0.40 | 0.847 | 0.000 | 0.040 | mixed | pass | **WATCH** |
  (power: n=1048 (n_eff=627), Sharpe=0.40, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+10.7bp/ev t=0.40 long%=66% L=+22.4 S=-12.3
  bb_p=0.157 (block=5)
  eras: 2020 n=34 net=-7174 | 2021 n=132 net=+11712 | 2022 n=148 net=+14838 | 2023 n=203 net=+3820 | 2024 n=196 net=-1319 | 2025 n=151 net=+2895 | 2026 n=184 net=-1421
  per-asset net: AVAX +2842 | BTC -1013 | DOGE +4639 | ETH +3419 | LINK +14118 | SOL +5562 | XRP -6216
  funding-carry adj: net=+33710bp (paid -10360bp carry; 100% of events have funding coverage)
| funding_consensus_drift_1d | 47 | 0.383 | 0.258 | FAIL | -2959 | -1.14 | 0.062 | 0.000 | 0.127 | consistent | pass | **KILL** |
  (power: n=47 (n_eff=47), Sharpe=-1.14, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-49.3bp/ev t=-1.18 long%=26% L=-66.8 S=-43.3
  bb_p=0.108 (block=5)
  eras: 2024 n=22 net=-1237 | 2025 n=25 net=-1722
  funding-carry adj: net=-2995bp (paid +36bp carry; 100% of events have funding coverage)
| lth_sopr_capitulation_7d | 105 | 0.448 | 0.356 | FAIL | -2616 | -0.38 | 0.204 | 0.000 | 0.848 | mixed | pass | **KILL** |
  (power: n=105 (n_eff=105), Sharpe=-0.38, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-59.4bp/ev t=-0.75 long%=100% L=-59.4 S=+nan
  bb_p=0.253 (block=5)
  eras: 2021 n=11 net=+834 | 2022 n=42 net=-4986 | 2023 n=3 net=+1266 | 2024 n=5 net=+2760 | 2025 n=19 net=-1667 | 2026 n=25 net=-823
  funding-carry adj: net=-3710bp (paid +1094bp carry; 100% of events have funding coverage)
| nrpl_spike_top_3d | 316 | 0.402 | 0.349 | FAIL | -66727 | -1.86 | 0.000 | 0.000 | 0.001 | consistent | pass | **KILL** |
  (power: n=316 (n_eff=316), Sharpe=-1.86, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-125.3bp/ev t=-2.43 long%=0% L=+nan S=-125.3
  bb_p=0.000 (block=5)
  eras: 2012 n=15 net=-926 | 2013 n=37 net=-25032 | 2014 n=1 net=+993 | 2015 n=26 net=-3853 | 2016 n=25 net=-3390 | 2017 n=59 net=-15387 | 2018 n=3 net=-886 | 2019 n=25 net=-5437 | 2020 n=25 net=-4167 | 2021 n=20 net=-3591 | 2023 n=34 net=-2828 | 2024 n=31 net=-1769 | 2025 n=10 net=+135 | 2026 n=5 net=-589
  funding-carry adj: net=-64229bp (paid -2498bp carry; 40% of events have funding coverage)
| exchange_balance_drift_7d | 254 | 0.524 | 0.462 | FAIL | -716 | -0.03 | 0.461 | 0.000 | 0.929 | mixed | pass | **KILL** |
  (power: n=254 (n_eff=254), Sharpe=-0.03, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+1.0bp/ev t=0.01 long%=52% L=+9.1 S=-7.6
  bb_p=0.529 (block=5)
  eras: 2012 n=11 net=-909 | 2013 n=31 net=-5235 | 2014 n=15 net=-509 | 2015 n=12 net=-6957 | 2016 n=21 net=-813 | 2017 n=29 net=+2414 | 2018 n=15 net=-6749 | 2019 n=15 net=+2285 | 2020 n=20 net=-675 | 2021 n=20 net=+11210 | 2022 n=23 net=+2834 | 2023 n=8 net=+2329 | 2024 n=24 net=-231 | 2025 n=10 net=+290
  funding-carry adj: net=-1014bp (paid +298bp carry; 43% of events have funding coverage)
