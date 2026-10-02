# Phase -1 Round 15 — LIVE-UNUSED-COLUMNS batch (5 hypotheses)

Declared pre-execution in manifest `round15_batch`. Coverage
audit 2026-09-28: these are the last economically distinct LIVE
inputs never consumed by any emitter. Daily clock; he-frame
c=px_bitstamp, us10y leg on harmony_daily c; publish-lagged
inputs; trailing-prior-day percentiles; drift-audit + n_eff live.
n_trials=53 effective families.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dormancy_spike_short_7d | 287 | 0 | 0.408 | 0.352 | FAIL | -87133 | -2.91 | 0.000 | 0.000 | 0.042 | consistent | pass | **KILL** |
  (power: n=287 (n_eff=287), Sharpe=-2.91, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-115.7bp/ev t=-1.65 long%=0% L=+nan S=-115.7
  bb_p=0.001 (block=5)
  eras: 2011 n=2 net=+1067 | 2012 n=11 net=-4566 | 2013 n=30 net=-34347 | 2014 n=22 net=+3724 | 2015 n=12 net=+4215 | 2016 n=21 net=-3868 | 2017 n=26 net=-15762 | 2018 n=14 net=-1506 | 2019 n=20 net=-1927 | 2020 n=18 net=-14579 | 2021 n=10 net=-2734 | 2022 n=21 net=-686 | 2023 n=26 net=-7942 | 2024 n=30 net=-7533 | 2025 n=20 net=-2035 | 2026 n=4 net=+1348
| hashrate_drawdown_long_14d | 163 | 0 | 0.546 | 0.469 | FAIL | 37470 | 2.05 | 1.000 | 0.004 | 0.834 | consistent | pass | **MODEL_RISK** |
  (power: n=163 (n_eff=163), Sharpe=2.05, MinTRL=343d, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-141.0bp/ev t=-1.26 long%=100% L=-141.0 S=+nan
  bb_p=0.026 (block=5)
  eras: 2012 n=4 net=+112 | 2013 n=2 net=+3791 | 2014 n=18 net=-9543 | 2015 n=15 net=+8880 | 2016 n=15 net=+10165 | 2017 n=12 net=+24038 | 2018 n=15 net=-3792 | 2019 n=8 net=-579 | 2020 n=9 net=+4203 | 2021 n=5 net=-4435 | 2022 n=9 net=-726 | 2023 n=10 net=-1577 | 2024 n=16 net=+7195 | 2025 n=15 net=+1432 | 2026 n=10 net=-1694
| us10y_shock_short_5d | 78 | 0 | 0.526 | 0.416 | FAIL | -7132 | -0.52 | 0.013 | 0.000 | 0.753 | mixed | pass | **KILL** |
  (power: n=78 (n_eff=78), Sharpe=-0.52, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+96.2bp/ev t=0.99 long%=0% L=+nan S=+96.2
  bb_p=0.174 (block=5)
  eras: 2010 n=7 net=-6580 | 2011 n=5 net=+1725 | 2012 n=2 net=+381 | 2013 n=7 net=-2969 | 2014 n=4 net=+1859 | 2015 n=6 net=-640 | 2016 n=7 net=-1418 | 2017 n=2 net=-2168 | 2018 n=5 net=+1331 | 2019 n=6 net=+2835 | 2020 n=2 net=-1137 | 2021 n=5 net=-1713 | 2022 n=8 net=+2447 | 2023 n=1 net=-1819 | 2024 n=2 net=+634 | 2025 n=1 net=-527 | 2026 n=8 net=+628
| realized_pl_ratio_capitulation_5d | 245 | 0 | 0.510 | 0.448 | FAIL | 2969 | 0.14 | 0.692 | 0.000 | 0.975 | consistent | pass | **KILL** |
  (power: n=245 (n_eff=245), Sharpe=0.14, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-105.5bp/ev t=-1.95 long%=100% L=-105.5 S=+nan
  bb_p=0.388 (block=5)
  eras: 2012 n=1 net=+131 | 2013 n=13 net=-4418 | 2014 n=35 net=+881 | 2015 n=16 net=+1010 | 2016 n=2 net=-148 | 2017 n=11 net=+6206 | 2018 n=39 net=-4623 | 2019 n=11 net=+4814 | 2020 n=6 net=+2194 | 2021 n=20 net=-443 | 2022 n=36 net=-5692 | 2023 n=4 net=+1150 | 2024 n=10 net=+3624 | 2025 n=20 net=+507 | 2026 n=21 net=-2225
| sth_mvrv_capitulation_7d | 27 | 0 | 0.556 | 0.373 | UNDERPOWERED | 1355 | 0.88 | 0.893 | 0.005 | 0.604 | mixed | pass | **UNDERPOWERED** |
  (power: n=27 < 30 minimum for directional resolution)
  drift-audit: skill=+38.5bp/ev t=0.35 long%=100% L=+38.5 S=+nan
  bb_p=nan (block=0)
  eras: 2024 n=7 net=+1390 | 2025 n=12 net=+330 | 2026 n=8 net=-365
