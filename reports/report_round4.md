# Phase -1 Round 4 — daily macro/on-chain families (Harmony export)

Data: `data_extended/harmony/macro_daily.parquet` — blockchain_api BTC
price (2010-2026), coinmetrics MVRV, alternative.me fng, Farside ETF
flows (2024+), Binance daily OI, coc funding, FRED. Verified: price
sanity at known dates, ETF pre-launch clean (NaN not 0), monotonic.
n_trials=17. Daily data => fewer independent events by construction.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| onchain_mvrv_regime | 91 | 0 | 0.407 | 0.311 | FAIL | -108613 | -3.73 | 0.000 | 0.000 | 0.005 | consistent | pass | **KILL** |
  (power: n=91 (n_eff=91), Sharpe=-3.73, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2011 n=5 net=-6390 | 2013 n=4 net=-42201 | 2014 n=7 net=-1172 | 2015 n=7 net=+252 | 2016 n=7 net=-4934 | 2017 n=11 net=-27491 | 2018 n=10 net=-3618 | 2019 n=2 net=+937 | 2020 n=5 net=-9749 | 2021 n=3 net=-5792 | 2022 n=10 net=-2555 | 2023 n=3 net=+752 | 2024 n=7 net=-6304 | 2025 n=3 net=-287 | 2026 n=7 net=-62
| fng_extreme_sentiment | 40 | 0 | 0.475 | 0.329 | FAIL | -2899 | -0.36 | 0.149 | 0.000 | 0.690 | mixed | pass | **KILL** |
  (power: n=40 (n_eff=40), Sharpe=-0.36, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.240 (block=5)
  eras: 2018 n=3 net=+5224 | 2019 n=2 net=-884 | 2020 n=11 net=-6033 | 2021 n=7 net=-288 | 2022 n=6 net=-384 | 2024 n=2 net=-1380 | 2025 n=2 net=-522 | 2026 n=7 net=+1367
| etf_flow_5d | 57 | 0 | 0.509 | 0.383 | FAIL | 1492 | 0.50 | 0.777 | 0.006 | 0.598 | mixed | pass | **WATCH** |
  (power: n=57 (n_eff=57), Sharpe=0.50, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.318 (block=5)
  eras: 2024 n=15 net=-777 | 2025 n=27 net=-575 | 2026 n=15 net=+2844
| cal_weekend_drift | 845 | 0 | 0.555 | 0.521 | PASS | 64731 | 1.41 | 1.000 | 0.001 | 0.757 | consistent | pass | **MODEL_RISK** |
  (power: n=845 (n_eff=845), Sharpe=1.41, MinTRL=1084d, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2010 n=24 net=+3664 | 2011 n=52 net=+4187 | 2012 n=52 net=-3404 | 2013 n=52 net=+20825 | 2014 n=52 net=-880 | 2015 n=52 net=+1894 | 2016 n=53 net=+4219 | 2017 n=52 net=+14927 | 2018 n=52 net=-3669 | 2019 n=52 net=+5479 | 2020 n=52 net=+5767 | 2021 n=53 net=+2514 | 2022 n=52 net=-2531 | 2023 n=52 net=+3561 | 2024 n=52 net=+5928 | 2025 n=52 net=+159 | 2026 n=39 net=+2091
| oi_price_divergence | 66 | 0 | 0.576 | 0.456 | FAIL | 6740 | 1.43 | 1.000 | 0.029 | 0.184 | consistent | pass | **WATCH** |
  (power: n=66 (n_eff=66), Sharpe=1.43, MinTRL=940d, MinBTL=20.7y@SR0.5)
  bb_p=0.043 (block=5)
  eras: 2020 n=1 net=-971 | 2021 n=10 net=+1303 | 2022 n=14 net=+3232 | 2023 n=8 net=+67 | 2024 n=16 net=+2869 | 2025 n=7 net=-2073 | 2026 n=10 net=+2314
