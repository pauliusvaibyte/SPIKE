# Phase -1 Round 10 — FLAGSHIP PORT (Sentinely base+N+V)

Cross-validation of upstream mega_screen's strongest retrospective
system inside this stack. Spec ported verbatim; 10bp RT (5bp/unit);
t+1 execution; events = invested days with turnover allocated inside
episodes. N-leg uses CM exchange flows (flash/provisional status —
declared limitation); V-leg uses harmony mvrv.
Universe: BTC max-clock + Binance perp BTC (2019+) + SOL,ETH,XRP,DOGE,AVAX,LINK HL daily. n_trials=40.

| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| flagship_base_btc | 3413 | 0.544 | 0.527 | PASS | 126256 | 1.67 | 1.000 | 0.001 | 0.000 | consistent | pass | **KILL** |
  (power: n=3413 (n_eff=63), Sharpe=1.67, MinTRL=764d, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2013 n=331 net=+46340 | 2014 n=153 net=-1463 | 2015 n=212 net=+4621 | 2016 n=354 net=+6755 | 2017 n=364 net=+27394 | 2018 n=103 net=-2698 | 2019 n=246 net=+8741 | 2020 n=306 net=+13305 | 2021 n=262 net=+8504 | 2022 n=95 net=-2692 | 2023 n=309 net=+7735 | 2024 n=300 net=+7759 | 2025 n=230 net=+932 | 2026 n=148 net=+1021
  strategy-stats: BTC: SR(10bp)=1.80 SR(15bp)=1.78 CAGR=1.61 MaxDD=-0.68 turnover=210.0
  buyhold-benchmark: Sharpe=1.23 CAGR=0.89 MaxDD=-0.85
| flagship_composite_btc | 3413 | 0.544 | 0.527 | PASS | 102866 | 1.77 | 1.000 | 0.002 | 0.003 | consistent | pass | **KILL** |
  (power: n=3413 (n_eff=63), Sharpe=1.77, MinTRL=647d, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2013 n=331 net=+33648 | 2014 n=153 net=-1422 | 2015 n=212 net=+3834 | 2016 n=354 net=+6500 | 2017 n=364 net=+20270 | 2018 n=103 net=-2495 | 2019 n=246 net=+7487 | 2020 n=306 net=+12566 | 2021 n=262 net=+7728 | 2022 n=95 net=-2250 | 2023 n=309 net=+7397 | 2024 n=300 net=+7949 | 2025 n=230 net=+644 | 2026 n=148 net=+1011
  strategy-stats: BTC: SR(10bp)=1.88 SR(15bp)=1.84 CAGR=1.26 MaxDD=-0.56 turnover=287.9
  buyhold-benchmark: Sharpe=1.23 CAGR=0.89 MaxDD=-0.85
| flagship_composite_hlbtc | 781 | 0.513 | 0.478 | FAIL | 14339 | 1.59 | 0.999 | 0.033 | 0.061 | consistent | pass | **UNDERPOWERED** |
  (power: n_eff=17 < 30 (span 1172d / median horizon 1d) — overlapping windows are not independent)
  bb_p=0.002 (block=5)
  eras: 2023 n=105 net=+4509 | 2024 n=300 net=+7987 | 2025 n=228 net=+602 | 2026 n=148 net=+1241
  strategy-stats: BTC: SR(10bp)=1.56 SR(15bp)=1.49 CAGR=0.48 MaxDD=-0.19 turnover=62.5
  buyhold-benchmark: Sharpe=0.97 CAGR=0.41 MaxDD=-0.53
| flagship_composite_bnbtc | 1669 | 0.515 | 0.491 | FAIL | 35799 | 1.60 | 1.000 | 0.004 | 0.017 | consistent | pass | **KILL** |
  (power: n=1669 (n_eff=36), Sharpe=1.60, MinTRL=754d, MinBTL=20.7y@SR0.5)
  bb_p=0.000 (block=5)
  eras: 2019 n=20 net=-384 | 2020 n=307 net=+13024 | 2021 n=261 net=+7920 | 2022 n=95 net=-2284 | 2023 n=309 net=+7681 | 2024 n=300 net=+7936 | 2025 n=229 net=+663 | 2026 n=148 net=+1242
  strategy-stats: BTC: SR(10bp)=1.59 SR(15bp)=1.53 CAGR=0.58 MaxDD=-0.35 turnover=115.1
  buyhold-benchmark: Sharpe=0.80 CAGR=0.34 MaxDD=-0.77
| flagship_base_alts | 3980 | 0.500 | 0.485 | FAIL | 98350 | 1.29 | 0.989 | 0.012 | 0.003 | consistent | pass | **UNDERPOWERED** |
  (power: n_eff=19 < 30 (span 1172d / median horizon 1d) — overlapping windows are not independent)
  bb_p=0.005 (block=7)
  eras: 2023 n=653 net=+42784 | 2024 n=1472 net=+42538 | 2025 n=1107 net=+3692 | 2026 n=748 net=+9337
  per-asset net: AVAX +13800 | DOGE +19507 | ETH +10954 | LINK +17419 | SOL +24698 | XRP +11973
  strategy-stats: SOL: SR(10bp)=1.31 SR(15bp)=1.29 CAGR=0.80 MaxDD=-0.47 turnover=51.0 | ETH: SR(10bp)=0.93 SR(15bp)=0.89 CAGR=0.31 MaxDD=-0.47 turnover=45.0 | XRP: SR(10bp)=0.72 SR(15bp)=0.68 CAGR=0.27 MaxDD=-0.52 turnover=58.0 | DOGE: SR(10bp)=0.98 SR(15bp)=0.96 CAGR=0.51 MaxDD=-0.54 turnover=35.5 | AVAX: SR(10bp)=0.76 SR(15bp)=0.73 CAGR=0.31 MaxDD=-0.56 turnover=53.0 | LINK: SR(10bp)=0.92 SR(15bp)=0.90 CAGR=0.44 MaxDD=-0.46 turnover=49.0
  buyhold-benchmark: Sharpe=0.97 CAGR=0.41 MaxDD=-0.53
| flagship_composite_alts | 3980 | 0.500 | 0.484 | FAIL | 87391 | 1.27 | 0.988 | 0.011 | 0.002 | consistent | pass | **UNDERPOWERED** |
  (power: n_eff=19 < 30 (span 1172d / median horizon 1d) — overlapping windows are not independent)
  bb_p=0.007 (block=8)
  eras: 2023 n=653 net=+42853 | 2024 n=1472 net=+35351 | 2025 n=1107 net=+77 | 2026 n=748 net=+9110
  per-asset net: AVAX +9793 | DOGE +17860 | ETH +11074 | LINK +16961 | SOL +21254 | XRP +10449
  strategy-stats: SOL: SR(10bp)=1.23 SR(15bp)=1.19 CAGR=0.66 MaxDD=-0.47 turnover=66.5 | ETH: SR(10bp)=1.02 SR(15bp)=0.96 CAGR=0.32 MaxDD=-0.42 turnover=56.2 | XRP: SR(10bp)=0.73 SR(15bp)=0.69 CAGR=0.25 MaxDD=-0.47 turnover=65.4 | DOGE: SR(10bp)=0.99 SR(15bp)=0.96 CAGR=0.48 MaxDD=-0.54 turnover=50.8 | AVAX: SR(10bp)=0.62 SR(15bp)=0.58 CAGR=0.20 MaxDD=-0.54 turnover=63.2 | LINK: SR(10bp)=1.00 SR(15bp)=0.97 CAGR=0.47 MaxDD=-0.42 turnover=57.8
  buyhold-benchmark: Sharpe=0.97 CAGR=0.41 MaxDD=-0.53
