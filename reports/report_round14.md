# Phase -1 Round 14 — WATCH-autopsy derivatives (4 hypotheses)

Declared pre-execution in manifest `round14_batch`. Derived from
the episode-gate autopsy: short-leg singles of the two candidates
whose only failing gate was ep-wilson, their union cluster, and
the carry edge concentrated to outer-5% funding (DSR-blocked parent).
Universe: BTC daily + BTC,ETH,SOL,XRP,DOGE,AVAX,LINK carry.
n_trials=51 effective families. Each variant is a new trial —
derivation is billed.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| oi_price_divergence_short | 40 | 0 | 0.600 | 0.446 | FAIL | 1933 | 0.44 | 0.849 | 0.000 | 0.620 | mixed | pass | **WATCH** |
  (power: n=40 (n_eff=40), Sharpe=0.44, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+102.5bp/ev t=0.97 long%=0% L=+nan S=+102.5
  bb_p=0.150 (block=5)
  eras: 2020 n=1 net=-971 | 2021 n=6 net=+1292 | 2022 n=10 net=+2351 | 2023 n=4 net=+463 | 2024 n=11 net=+616 | 2025 n=4 net=-1163 | 2026 n=4 net=-656
| equity_lead_btc_5d_short | 121 | 0 | 0.521 | 0.432 | FAIL | 10960 | 0.56 | 0.989 | 0.000 | 0.770 | mixed | pass | **WATCH** |
  (power: n=121 (n_eff=121), Sharpe=0.56, MinTRL=267032d, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+276.5bp/ev t=3.04 long%=0% L=+nan S=+276.5
  bb_p=0.163 (block=5)
  eras: 2010 n=1 net=-553 | 2011 n=13 net=+11796 | 2012 n=4 net=-331 | 2013 n=3 net=-3195 | 2014 n=8 net=+504 | 2015 n=11 net=-417 | 2016 n=7 net=+431 | 2017 n=2 net=-2598 | 2018 n=14 net=+4520 | 2019 n=1 net=-1053 | 2020 n=8 net=+597 | 2021 n=8 net=-4781 | 2022 n=19 net=+7846 | 2023 n=4 net=-1374 | 2024 n=6 net=-1375 | 2025 n=5 net=+379 | 2026 n=7 net=+565
| riskoff_cluster_5d | 149 | 0 | 0.517 | 0.437 | FAIL | 8238 | 0.40 | 0.947 | 0.000 | 0.870 | consistent | pass | **WATCH** |
  (power: n=149 (n_eff=149), Sharpe=0.40, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+241.2bp/ev t=3.09 long%=0% L=+nan S=+241.2
  bb_p=0.245 (block=5)
  eras: 2010 n=1 net=-553 | 2011 n=13 net=+11796 | 2012 n=4 net=-331 | 2013 n=3 net=-3195 | 2014 n=8 net=+504 | 2015 n=11 net=-417 | 2016 n=7 net=+431 | 2017 n=2 net=-2598 | 2018 n=14 net=+4520 | 2019 n=1 net=-1053 | 2020 n=9 net=-374 | 2021 n=13 net=-3858 | 2022 n=26 net=+8245 | 2023 n=7 net=-1033 | 2024 n=15 net=-2066 | 2025 n=8 net=-1538 | 2026 n=7 net=-241
| funding_carry_extreme | 1710 | 627 | 0.515 | 0.492 | FAIL | -23873 | -0.58 | 0.184 | 0.000 | 0.691 | mixed | pass | **KILL** |
  (power: n=1710 (n_eff=276), Sharpe=-0.58, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+27.4bp/ev t=1.59 long%=77% L=+32.8 S=+5.3
  bb_p=0.189 (block=5)
  eras: 2024 n=261 net=-10560 | 2025 n=660 net=+12215 | 2026 n=789 net=-25528
  per-asset net: AVAX -1397 | BTC +4841 | DOGE -6502 | ETH -4765 | LINK +4743 | SOL -7083 | XRP -13712
