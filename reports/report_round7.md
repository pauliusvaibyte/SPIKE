# Phase -1 Round 7 — 40/125 DMA cross (TREND-family retest)

Declared pre-execution in manifest `round7_dmaretest`. Retest billed
to TREND: same mechanism (trend persistence) at materially longer
timescale than the killed TREND-1/TREND-2 variants. Golden cross ->
LONG, death cross -> SHORT; 1d eval +30d, 4h eval +30 bars (5d).
Universe: BTC,SOL,ETH,XRP,DOGE,AVAX,LINK. n_trials=26.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dma_40_125_cross_1d | 70 | 4 | 0.571 | 0.455 | FAIL | 53371 | 4.03 | 1.000 | 0.999 | 0.061 | consistent | pass | **BLOCKED** |
  (power: n_eff=10 < 30 (span 1070d / median horizon 30d) — overlapping windows are not independent)
  bb_p=0.133 (block=5)
  eras: 2023 n=6 net=+25830 | 2024 n=22 net=+25313 | 2025 n=29 net=+8464 | 2026 n=13 net=-6236
  per-asset net: AVAX +14430 | BTC +4560 | DOGE +21419 | ETH +7721 | LINK +12186 | SOL +9031 | XRP -15975
| dma_40_125_cross_4h | 324 | 0 | 0.534 | 0.480 | FAIL | -6931 | -0.45 | 0.249 | 0.000 | 0.844 | mixed | pass | **KILL** |
  (power: n=324 (n_eff=42), Sharpe=-0.45, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.395 (block=5)
  eras: 2024 n=73 net=+13444 | 2025 n=141 net=-18242 | 2026 n=110 net=-2134
  per-asset net: AVAX -1203 | BTC +2036 | DOGE +4498 | ETH -6645 | LINK -22 | SOL -3473 | XRP -2123
