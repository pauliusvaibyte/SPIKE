# Phase -1 Round 9 — mechanism-diverse batch (10 hypotheses)

Declared pre-execution in manifest `round9_batch`. Families:
VOL-REGIME, CARRY, SESSION, BREADTH, VOLUME-CLIMAX (retest),
ROTATION. Deliberately non-momentum-themed.
Universe: BTC,SOL,ETH,XRP,DOGE,AVAX,LINK. n_trials=39.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| compression_breakout_4h | 388 | 0 | 0.503 | 0.453 | FAIL | -4079 | -0.22 | 0.378 | 0.000 | 0.981 | mixed | pass | **KILL** |
  (power: n=388 (n_eff=150), Sharpe=-0.22, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.378 (block=5)
  eras: 2024 n=26 net=-630 | 2025 n=173 net=-7663 | 2026 n=189 net=+4214
  per-asset net: AVAX -5207 | BTC -1098 | DOGE -3341 | ETH +3461 | LINK +4175 | SOL -3560 | XRP +1490
| funding_carry_24h | 3438 | 826 | 0.528 | 0.511 | PASS | 11229 | 0.20 | 0.619 | 0.000 | 0.055 | mixed | pass | **WATCH** |
  (power: n=3438 (n_eff=129), Sharpe=0.20, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.373 (block=6)
  eras: 2024 n=572 net=-9027 | 2025 n=1219 net=+17932 | 2026 n=1647 net=+2324
  per-asset net: AVAX +8444 | BTC +7427 | DOGE +9831 | ETH -7408 | LINK +6738 | SOL -3041 | XRP -10761
| us_session_drift | 5887 | 7 | 0.479 | 0.466 | FAIL | -55400 | -0.63 | 0.173 | 0.000 | 0.925 | consistent | pass | **KILL** |
  (power: n=5887 (n_eff=841), Sharpe=-0.63, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.133 (block=10)
  eras: 2024 n=1421 net=-5204 | 2025 n=2555 net=-43772 | 2026 n=1911 net=-6423
  per-asset net: AVAX -12292 | BTC -7449 | DOGE -4817 | ETH -9922 | LINK -5264 | SOL -13673 | XRP -1983
| asia_session_drift | 5889 | 0 | 0.517 | 0.504 | PASS | -39820 | -0.72 | 0.133 | 0.000 | 0.407 | consistent | pass | **KILL** |
  (power: n=5889 (n_eff=842), Sharpe=-0.72, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.090 (block=7)
  eras: 2024 n=1423 net=+22298 | 2025 n=2555 net=-29176 | 2026 n=1911 net=-32943
  per-asset net: AVAX -6237 | BTC -8353 | DOGE -4915 | ETH -7511 | LINK -4409 | SOL -2154 | XRP -6239
| us_session_momentum | 5872 | 7 | 0.484 | 0.471 | FAIL | -68241 | -0.78 | 0.118 | 0.000 | 0.738 | mixed | pass | **KILL** |
  (power: n=5872 (n_eff=840), Sharpe=-0.78, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.089 (block=7)
  eras: 2024 n=1417 net=-49961 | 2025 n=2555 net=-33812 | 2026 n=1900 net=+15532
  per-asset net: AVAX -16060 | BTC -7481 | DOGE -1554 | ETH -15294 | LINK -2679 | SOL -8869 | XRP -16304
| breadth_thrust_1d | 2968 | 0 | 0.488 | 0.470 | FAIL | 19793 | 0.25 | 0.676 | 0.000 | 0.357 | mixed | pass | **WATCH** |
  (power: n=2968 (n_eff=424), Sharpe=0.25, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.283 (block=7)
  eras: 2023 n=504 net=-6323 | 2024 n=889 net=+24087 | 2025 n=889 net=-9743 | 2026 n=686 net=+11771
  per-asset net: AVAX +6485 | BTC -2859 | DOGE +5130 | ETH +1296 | LINK +2980 | SOL -2517 | XRP +9277
| breadth_washout_1d | 3038 | 0 | 0.506 | 0.488 | FAIL | -4534 | -0.05 | 0.466 | 0.000 | 0.779 | mixed | pass | **KILL** |
  (power: n=3038 (n_eff=434), Sharpe=-0.05, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.433 (block=7)
  eras: 2023 n=476 net=+33915 | 2024 n=819 net=+7116 | 2025 n=973 net=-26529 | 2026 n=770 net=-19036
  per-asset net: AVAX -5903 | BTC -797 | DOGE -5025 | ETH -5656 | LINK +680 | SOL +8520 | XRP +3646
| volume_divergence_fade_1d | 456 | 0 | 0.491 | 0.446 | FAIL | -19187 | -1.15 | 0.019 | 0.000 | 0.121 | mixed | pass | **KILL** |
  (power: n=456 (n_eff=285), Sharpe=-1.15, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.011 (block=5)
  eras: 2023 n=60 net=+1119 | 2024 n=155 net=-1269 | 2025 n=159 net=-12682 | 2026 n=82 net=-6356
  per-asset net: AVAX -3568 | BTC -1231 | DOGE -7869 | ETH -274 | LINK -411 | SOL -3418 | XRP -2415
| btc_alt_rotation_3d | 267 | 1 | 0.506 | 0.446 | FAIL | -6979 | -0.37 | 0.256 | 0.000 | 0.742 | mixed | pass | **KILL** |
  (power: n=267 (n_eff=107), Sharpe=-0.37, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.351 (block=5)
  eras: 2023 n=39 net=-3045 | 2024 n=101 net=-5903 | 2025 n=76 net=+5422 | 2026 n=51 net=-3453
  per-asset net: AVAX -413 | DOGE -4769 | ETH +1251 | LINK +6834 | SOL -5849 | XRP -4034
| weekly_loser_bounce_1d | 621 | 5 | 0.488 | 0.449 | FAIL | -34781 | -1.90 | 0.000 | 0.000 | 0.317 | consistent | pass | **UNDERPOWERED** |
  (power: n_eff=8 < 30 (span 1209d / median horizon 7d) — overlapping windows are not independent)
  bb_p=0.120 (block=5)
  eras: 2023 n=101 net=-16074 | 2024 n=185 net=-13954 | 2025 n=191 net=-5110 | 2026 n=144 net=+357
  per-asset net: AVAX -17181 | BTC -4177 | DOGE -12301 | ETH -5572 | LINK +6097 | SOL -884 | XRP -763
