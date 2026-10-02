# Phase -1 Round 13 — walk-forward selection replay

Screen the flagship rule grid on data <= C only, then evaluate the
selected config on C -> end. Selection must transfer OOS or the
flagship's support is selection luck. Costs: strategy_stats @10bp
IS-select; OOS reported at 10/20/30bp. Clock: px_bitstamp.

## cutoff 2017-01-01
- IS-selected: f=45 s=200 k=5 a=0.6 damper=NV (in-sample Sharpe 2.02, 288 eligible configs)
- OOS 2017-01-01->end: Sharpe@10bp=1.35 @20bp=1.27 @30bp=1.22 DSR@10bp=1.000 CAGR=0.56 MaxDD=-0.53
- OOS buyhold: Sharpe=1.01 CAGR=0.57 MaxDD=-0.83
- OOS actual-flagship (45/125/5/0.5+NV): Sharpe@10bp=1.59 CAGR=0.71
- top-5 IS configs: (45, 200, 5, 0.6, 'NV')(SR 2.02); (45, 200, 10, 0.6, 'NV')(SR 2.02); (45, 200, 5, 0.5, 'NV')(SR 2.02); (60, 200, 5, 0.6, 'NV')(SR 2.02); (45, 200, 10, 0.5, 'NV')(SR 2.01)

## cutoff 2019-01-01
- IS-selected: f=45 s=200 k=5 a=0.6 damper=NV (in-sample Sharpe 1.91, 288 eligible configs)
- OOS 2019-01-01->end: Sharpe@10bp=1.30 @20bp=1.22 @30bp=1.16 DSR@10bp=0.999 CAGR=0.48 MaxDD=-0.42
- OOS buyhold: Sharpe=0.95 CAGR=0.49 MaxDD=-0.77
- OOS actual-flagship (45/125/5/0.5+NV): Sharpe@10bp=1.58 CAGR=0.64
- top-5 IS configs: (45, 200, 5, 0.6, 'NV')(SR 1.91); (45, 200, 10, 0.6, 'NV')(SR 1.90); (45, 200, 5, 0.5, 'NV')(SR 1.90); (45, 200, 10, 0.5, 'NV')(SR 1.90); (45, 200, 5, 0.4, 'NV')(SR 1.88)

## cutoff 2021-01-01
- IS-selected: f=45 s=125 k=5 a=0.6 damper=NV (in-sample Sharpe 1.90, 288 eligible configs)
- OOS 2021-01-01->end: Sharpe@10bp=1.27 @20bp=1.18 @30bp=1.12 DSR@10bp=0.998 CAGR=0.40 MaxDD=-0.36
- OOS buyhold: Sharpe=0.57 CAGR=0.18 MaxDD=-0.77
- OOS actual-flagship (45/125/5/0.5+NV): Sharpe@10bp=1.28 CAGR=0.40
- top-5 IS configs: (45, 125, 5, 0.6, 'NV')(SR 1.90); (45, 125, 10, 0.6, 'NV')(SR 1.90); (45, 200, 5, 0.6, 'NV')(SR 1.90); (45, 125, 5, 0.5, 'NV')(SR 1.90); (45, 125, 10, 0.5, 'NV')(SR 1.89)

## cutoff 2023-01-01
- IS-selected: f=45 s=125 k=10 a=0.6 damper=NV (in-sample Sharpe 1.76, 288 eligible configs)
- OOS 2023-01-01->end: Sharpe@10bp=1.47 @20bp=1.36 @30bp=1.29 DSR@10bp=0.996 CAGR=0.48 MaxDD=-0.19
- OOS buyhold: Sharpe=1.15 CAGR=0.54 MaxDD=-0.53
- OOS actual-flagship (45/125/5/0.5+NV): Sharpe@10bp=1.55 CAGR=0.52
- top-5 IS configs: (45, 125, 10, 0.6, 'NV')(SR 1.76); (45, 125, 5, 0.6, 'NV')(SR 1.76); (45, 125, 10, 0.5, 'NV')(SR 1.76); (45, 125, 5, 0.5, 'NV')(SR 1.76); (45, 125, 10, 0.6, 'N')(SR 1.75)

# Leads replay — direction + threshold re-derived per cutoff

## nrpl(one-sided hi) @2019-01-01
- IS-selected: mode=long pct=(0.15,0.85) IS n=217 net=+54574bp
- OOS: n=190 hit=0.558 net=+13131bp
## nrpl(one-sided hi) @2021-01-01
- IS-selected: mode=long pct=(0.2,0.8) IS n=325 net=+63901bp
- OOS: n=162 hit=0.549 net=+10682bp
## nrpl(one-sided hi) @2023-01-01
- IS-selected: mode=long pct=(0.2,0.8) IS n=355 net=+66570bp
- OOS: n=133 hit=0.571 net=+9419bp
## nrpl(one-sided hi) @2025-01-01
- IS-selected: mode=long pct=(0.2,0.8) IS n=459 net=+74726bp
- OOS: n=28 hit=0.536 net=+1184bp

## puell @2019-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=223 net=+78768bp
- OOS: n=217 hit=0.548 net=+22663bp
## puell @2021-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=271 net=+80170bp
- OOS: n=169 hit=0.556 net=+17812bp
## puell @2023-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=330 net=+93261bp
- OOS: n=111 hit=0.541 net=+7315bp
## puell @2025-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=395 net=+96090bp
- OOS: n=46 hit=0.565 net=+4486bp

## reserve_risk @2019-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=217 net=+84792bp
- OOS: n=170 hit=0.529 net=+9359bp
## reserve_risk @2021-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=255 net=+80222bp
- OOS: n=132 hit=0.553 net=+12201bp
## reserve_risk @2023-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=322 net=+94580bp
- OOS: n=66 hit=0.515 net=-266bp
## reserve_risk @2025-01-01
- IS-selected: mode=cont pct=(0.2,0.8) IS n=368 net=+95395bp
- OOS: n=19 hit=0.316 net=-1580bp

## skew25_1m @2019-01-01: no config reached IS n>=15
## skew25_1m @2021-01-01: no config reached IS n>=15
## skew25_1m @2023-01-01
- IS-selected: mode=cont pct=(0.15,0.85) IS n=43 net=+5054bp
- OOS: n=108 hit=0.417 net=-12232bp
## skew25_1m @2025-01-01
- IS-selected: mode=revert pct=(0.1,0.9) IS n=87 net=+3111bp
- OOS: n=26 hit=0.538 net=-272bp

## premium_basis @2021-01-01
- IS-selected: mode=runaway p=0.95 IS n=17 net=+9314bp
- OOS: n=534 hit=0.427 net=-24302bp
## premium_basis @2023-01-01
- IS-selected: mode=converge p=0.9 IS n=314 net=+19375bp
- OOS: n=734 hit=0.535 net=+3975bp
## premium_basis @2025-01-01
- IS-selected: mode=converge p=0.9 IS n=713 net=+21876bp
- OOS: n=335 hit=0.516 net=+1475bp

## fng_fear @2019-01-01
- IS-selected: mode=long fear=20 IS n=16 net=+2479bp
- OOS: n=75 hit=0.533 net=+4248bp
## fng_fear @2021-01-01
- IS-selected: mode=long fear=20 IS n=34 net=+5359bp
- OOS: n=57 hit=0.474 net=+1368bp
## fng_fear @2023-01-01
- IS-selected: mode=long fear=10 IS n=17 net=+9666bp
- OOS: n=9 hit=0.667 net=+845bp
## fng_fear @2025-01-01
- IS-selected: mode=long fear=10 IS n=17 net=+9666bp
- OOS: n=9 hit=0.667 net=+845bp

## mom24h(binance BTC 4h) @2021-01-01
- IS-selected: mode=fade horizon=6 IS n=479 net=-1928bp
- OOS: n=2098 hit=0.531 net=-7712bp

## mom24h(binance BTC 4h) @2023-01-01
- IS-selected: mode=fade horizon=6 IS n=1209 net=-1573bp
- OOS: n=1368 hit=0.526 net=-8093bp

## mom24h(binance BTC 4h) @2025-01-01
- IS-selected: mode=cont horizon=8 IS n=1455 net=+7905bp
- OOS: n=477 hit=0.463 net=-4139bp
