# Phase -1 Round 16 — basis1_premium_p10 mechanism audit

reconcile vs events_extended: MATCH (rows 900 vs 900, covered 606 vs 606, net 3723 vs 3723)

covered events n=606  net=+3723bp  hit=0.513

| candidate | n | hit | net_bp | **verdict** |
|---|---|---|---|---|
| basis1_premium_p10_enriched | 606 | 0.553 | 3723.1 | **KILL** |

## Sub-period robustness

| quarter | n | net_bp |
|---|---|---|
| 2024-06-30 | 25 | -633 |
| 2024-09-30 | 81 | +118 |
| 2024-12-31 | 61 | +374 |
| 2025-03-31 | 91 | -575 |
| 2025-06-30 | 61 | +2289 |
| 2025-09-30 | 58 | +237 |
| 2025-12-31 | 68 | +1754 |
| 2026-03-31 | 83 | -1038 |
| 2026-06-30 | 35 | +772 |
| 2026-09-30 | 43 | +425 |

leave-one-year-out: ex-2024: net +3864bp (n=439) | ex-2025: net +19bp (n=328) | ex-2026: net +3564bp (n=445)

## Cluster concentration

top-5 events: +5171bp = 139% of total net (cap 60%) | effective episodes n_eff=261

## Dose-response (deeper dislocation should earn more)

deep (prem<=p5): n=330 mean=-8.2bp net=-2721bp hit=0.479
shallow (p5<prem<=p10): n=276 mean=+23.3bp net=+6444bp hit=0.554

## Convergence (premium should normalize toward median during hold)

median premium delta over hold: +1.31e-04 | share converged upward: 0.795 | median prem_in=-5.57e-04 p50=-7.98e-05

## Placebo re-check

time-shift p=0.040 real_mean=+16.1bp n_perm=1000

## Verdict (declared kill rule)

- trigger: top-5 = 139% of net (>60%)
- trigger: no dose-response (deep -8.2 <= shallow +23.3)
**KILL**