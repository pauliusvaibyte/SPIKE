# Phase -1 Round 8 — throughput batch (10 hypotheses)

Declared pre-execution in manifest `round8_batch`. Mechanisms:
vol shock, volume climax, funding flip, trapped squeeze, alt
residual reversal, drawdown capitulation, month-end rebalancing,
taker share (2y retest), VIX spike, RSI-2 (MRV retest).
Universe: BTC,SOL,ETH,XRP,DOGE,AVAX,LINK. n_trials=34.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rv_spike_fade_4h | 1312 | 0 | 0.520 | 0.493 | FAIL | -18867 | -0.89 | 0.100 | 0.000 | 0.335 | mixed | pass | **KILL** |
  (power: n=1312 (n_eff=562), Sharpe=-0.89, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.071 (block=5)
  eras: 2024 n=288 net=+4643 | 2025 n=590 net=-8644 | 2026 n=434 net=-14866
  per-asset net: AVAX +897 | BTC -1883 | DOGE -4674 | ETH -3122 | LINK -3943 | SOL -2522 | XRP -3619
| volume_climax_fade | 402 | 0 | 0.515 | 0.466 | FAIL | -5219 | -0.42 | 0.284 | 0.000 | 0.720 | mixed | pass | **KILL** |
  (power: n=402 (n_eff=256), Sharpe=-0.42, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.261 (block=5)
  eras: 2024 n=116 net=+3116 | 2025 n=223 net=-7277 | 2026 n=63 net=-1058
  per-asset net: AVAX +750 | BTC -947 | DOGE +1316 | ETH -3647 | LINK +923 | SOL -2968 | XRP -646
| funding_flip_momentum | 10080 | 3091 | 0.500 | 0.490 | FAIL | -107860 | -3.48 | 0.000 | 0.000 | 0.878 | consistent | pass | **KILL** |
  (power: n=10080 (n_eff=78), Sharpe=-3.48, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=6)
  eras: 2024 n=1570 net=-15110 | 2025 n=4207 net=-51985 | 2026 n=4303 net=-40764
  per-asset net: AVAX -15768 | BTC -11230 | DOGE -15016 | ETH -23363 | LINK -11231 | SOL -17338 | XRP -13915
| trapped_positioning_squeeze | 1687 | 0 | 0.481 | 0.457 | FAIL | -21431 | -0.49 | 0.231 | 0.000 | 0.838 | consistent | pass | **KILL** |
  (power: n=1687 (n_eff=313), Sharpe=-0.49, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.207 (block=5)
  eras: 2024 n=434 net=+1074 | 2025 n=812 net=-18689 | 2026 n=441 net=-3816
  per-asset net: AVAX -240 | BTC -3063 | DOGE +1519 | ETH +3450 | LINK -9581 | SOL -6728 | XRP -6788
| alt_resid_reversal_1d | 473 | 0 | 0.467 | 0.423 | FAIL | -31036 | -1.29 | 0.013 | 0.000 | 0.003 | consistent | pass | **KILL** |
  (power: n=473 (n_eff=301), Sharpe=-1.29, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.005 (block=5)
  eras: 2023 n=3 net=+74 | 2024 n=201 net=-30049 | 2025 n=166 net=+1753 | 2026 n=103 net=-2815
  per-asset net: AVAX -7152 | DOGE -14856 | ETH -4567 | LINK +1887 | SOL -2500 | XRP -3848
| drawdown_bounce_1d | 693 | 0 | 0.481 | 0.444 | FAIL | 16412 | 0.54 | 0.833 | 0.000 | 0.910 | mixed | pass | **UNDERPOWERED** |
  (power: n_eff=24 < 30 (span 1174d / median horizon 7d) — overlapping windows are not independent)
  bb_p=0.393 (block=6)
  eras: 2023 n=74 net=+11251 | 2024 n=210 net=+36299 | 2025 n=231 net=-13369 | 2026 n=178 net=-17769
  per-asset net: AVAX -11033 | BTC +3589 | DOGE +8707 | ETH -1463 | LINK +4228 | SOL +9152 | XRP +3232
| month_end_drift_1d | 546 | 14 | 0.527 | 0.486 | FAIL | 3397 | 0.07 | 0.552 | 0.000 | 0.718 | mixed | pass | **KILL** |
  (power: n=546 (n_eff=39), Sharpe=0.07, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.472 (block=10)
  eras: 2023 n=98 net=+17475 | 2024 n=168 net=-5174 | 2025 n=168 net=+2418 | 2026 n=112 net=-11322
  per-asset net: AVAX -1266 | BTC -892 | DOGE -478 | ETH -4886 | LINK +3409 | SOL +1271 | XRP +6240
| taker_share_fade_1h | 3845 | 8532 | 0.512 | 0.497 | FAIL | -41133 | -12.25 | 0.000 | 0.000 | 0.487 | consistent | pass | **KILL** |
  (power: n=3845 (n_eff=2362), Sharpe=-12.25, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2026 n=3845 net=-41133
  per-asset net: AVAX -4683 | BTC -5646 | DOGE -7488 | ETH -8795 | LINK -3105 | SOL -5687 | XRP -5729
| vix_spike_btc_long | 204 | 0 | 0.529 | 0.461 | FAIL | 34963 | 1.15 | 1.000 | 0.000 | 0.409 | consistent | pass | **MODEL_RISK** |
  (power: n=204 (n_eff=204), Sharpe=1.15, MinTRL=1747d, MinBTL=20.7y@SR0.5)
  bb_p=0.012 (block=5)
  eras: 2010 n=1 net=-999 | 2011 n=19 net=+362 | 2012 n=11 net=+2789 | 2013 n=13 net=+10868 | 2014 n=16 net=-3911 | 2015 n=12 net=+4639 | 2016 n=10 net=+2207 | 2017 n=7 net=+8656 | 2018 n=19 net=+1378 | 2019 n=8 net=+4028 | 2020 n=13 net=+2652 | 2021 n=15 net=+5563 | 2022 n=13 net=-2352 | 2023 n=9 net=+3356 | 2024 n=16 net=-18 | 2025 n=11 net=-2586 | 2026 n=11 net=-1668
| rsi2_connors_1d | 2906 | 1 | 0.508 | 0.490 | FAIL | -54737 | -0.78 | 0.076 | 0.000 | 0.272 | consistent | pass | **KILL** |
  (power: n=2906 (n_eff=922), Sharpe=-0.78, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.074 (block=7)
  eras: 2023 n=493 net=-1804 | 2024 n=844 net=-40894 | 2025 n=909 net=+17390 | 2026 n=660 net=-29429
  per-asset net: AVAX -5969 | BTC -7523 | DOGE -17176 | ETH -2244 | LINK +972 | SOL -11151 | XRP -11645
