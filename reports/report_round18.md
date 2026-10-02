# Phase -1 Round 18 — DVOL retest (provider-native Deribit feed)

Declared pre-execution in manifest `round18_dvol`. BILLED to
OPTIONS-VOL — horizon/param retests of killed dvol_spike_bounce_1d
(round11: +1d on harmony dvol_close, n=138 hit .471 KILL). Prior:
KILL expected; value is native-feed freshness (+7mo past harmony's
2026-02-19 cutoff) and +5d horizon coverage.

join coverage: 1215/2016 DVOL days matched to BTC closes

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dvol_spike_btc_long | 39 | 0 | 0.487 | 0.339 | FAIL | 2573 | 1.01 | 0.961 | 0.002 | 0.493 | mixed | pass | **MODEL_RISK** |
  (power: n=39 (n_eff=39), Sharpe=1.01, MinTRL=3645d, MinBTL=20.7y@SR0.5)
  bb_p=0.383 (block=9)
  eras: 2023 n=6 net=+1683 | 2024 n=12 net=+3362 | 2025 n=12 net=-1636 | 2026 n=9 net=-836
| dvol_level_long | 23 | 0 | 0.348 | 0.188 | UNDERPOWERED | -1457 | -0.95 | 0.070 | 0.000 | 0.638 | mixed | pass | **UNDERPOWERED** |
  (power: n=23 < 30 minimum for directional resolution)
  bb_p=nan (block=0)
  eras: 2023 n=6 net=+415 | 2024 n=9 net=-1170 | 2025 n=2 net=+679 | 2026 n=6 net=-1382
