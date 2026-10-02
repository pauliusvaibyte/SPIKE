# Phase -1 Round 6 — cross-sectional expansion + new-mechanism batch

Declared pre-execution in manifest `round6_candidates`. Universe:
BTC,SOL,ETH,XRP,DOGE,AVAX,LINK on data_extended/. Mechanisms:
xasset lead/lag, funding RV vs basket, HL premium dislocation,
funding duration, 15m bounce, equity beta, OI crowding, taker
toxicity. n_trials=26.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| xasset_btc_leads_alts | 2226 | 0 | 0.444 | 0.424 | FAIL | -29825 | -4.33 | 0.001 | 0.000 | 0.019 | consistent | pass | **KILL** |
  (power: n=2226 (n_eff=371), Sharpe=-4.33, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.001 (block=8)
  eras: 2026 n=2226 net=-29825
  per-asset net: AVAX -4538 | DOGE -5328 | ETH -4194 | LINK -5881 | SOL -5306 | XRP -4577
| funding_xasset_rv | 4056 | 1528 | 0.499 | 0.484 | FAIL | -100388 | -1.97 | 0.001 | 0.000 | 0.025 | consistent | pass | **KILL** |
  (power: n=4056 (n_eff=162), Sharpe=-1.97, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2024 n=1174 net=-36787 | 2025 n=1530 net=-39953 | 2026 n=1352 net=-23648
  per-asset net: AVAX +25727 | BTC +9979 | DOGE -59566 | ETH -13262 | LINK -21102 | SOL -10322 | XRP -31842
| hl_premium_disloc | 6453 | 3100 | 0.496 | 0.484 | FAIL | -134635 | -1.62 | 0.003 | 0.000 | 0.000 | consistent | pass | **KILL** |
  (power: n=6453 (n_eff=713), Sharpe=-1.62, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.001 (block=12)
  eras: 2024 n=2116 net=-96575 | 2025 n=2135 net=-24695 | 2026 n=2202 net=-13365
  per-asset net: AVAX +2591 | BTC -4405 | DOGE -37598 | ETH -19702 | LINK -20536 | SOL -4934 | XRP -50052
| funding_run_persistence | 969 | 329 | 0.499 | 0.468 | FAIL | -14654 | -0.66 | 0.154 | 0.000 | 0.730 | mixed | pass | **KILL** |
  (power: n=969 (n_eff=323), Sharpe=-0.66, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.183 (block=5)
  eras: 2024 n=170 net=-3049 | 2025 n=417 net=-7048 | 2026 n=382 net=-4557
  per-asset net: AVAX +634 | BTC +1347 | DOGE -9382 | ETH -6854 | LINK +1068 | SOL -298 | XRP -1168
| serialcorr_15m_bounce | 4572 | 0 | 0.524 | 0.510 | PASS | -50929 | -14.30 | 0.000 | 0.000 | 0.041 | consistent | pass | **KILL** |
  (power: n=4572 (n_eff=1710), Sharpe=-14.30, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=8)
  eras: 2026 n=4572 net=-50929
  per-asset net: AVAX -5527 | BTC -6056 | DOGE -8041 | ETH -6291 | LINK -8708 | SOL -8963 | XRP -7342
| equity_lead_btc_5d | 236 | 0 | 0.500 | 0.437 | FAIL | 23124 | 0.77 | 1.000 | 0.000 | 0.146 | consistent | pass | **WATCH** |
  (power: n=236 (n_eff=236), Sharpe=0.77, MinTRL=11551d, MinBTL=20.7y@SR0.5)
  bb_p=0.072 (block=5)
  eras: 2010 n=3 net=+2140 | 2011 n=24 net=+8368 | 2012 n=7 net=+1327 | 2013 n=11 net=-1464 | 2014 n=14 net=-2510 | 2015 n=22 net=+765 | 2016 n=12 net=+704 | 2017 n=8 net=+5344 | 2018 n=26 net=+3610 | 2019 n=5 net=-989 | 2020 n=14 net=+1324 | 2021 n=17 net=-3000 | 2022 n=26 net=+7507 | 2023 n=8 net=-1444 | 2024 n=15 net=+77 | 2025 n=10 net=+155 | 2026 n=14 net=+1211
| oi_crowding_fade | 1 | 0 | 0.000 | 0.000 | UNDERPOWERED | -64 | 0.00 | nan | nan | nan | mixed | pass | **UNDERPOWERED** |
  (power: n=1 < 30 minimum for directional resolution)
  bb_p=nan (block=0)
  eras: 2026 n=1 net=-64
| taker_toxicity_1h | 95 | 0 | 0.505 | 0.406 | FAIL | -937 | -6.87 | 0.063 | 0.021 | 0.979 | consistent | pass | **UNDERPOWERED** |
  (power: span=18d < 30d minimum — clustered events are not independent observations)
  bb_p=0.084 (block=5)
  eras: 2026 n=95 net=-937
  per-asset net: BTC -768 | SOL -169
