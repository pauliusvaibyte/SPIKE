# Phase -1 Round 3 — new-mechanism families (extended data)

Declared pre-execution in manifest `round3_candidates`. Mechanisms:
settlement cash-flow drift, cross-venue funding dislocation,
cross-venue lead/lag, cross-venue price-basis convergence.
Data: HL funding to launch, HL 1h (208d) / 4h (833d) bars,
Binance funding (2019+) + 1h klines (~2y). n_trials=13.

| candidate | n | n_uncov | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| settle1_funding_drift | 5591 | 32058 | 0.489 | 0.476 | FAIL | -56898 | -13.61 | 0.000 | 0.000 | 0.836 | consistent | pass | **KILL** |
  (power: n=5591 (n_eff=3859), Sharpe=-13.61, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+0.5bp/ev t=0.56
  bb_p=0.000 (block=5)
  eras: 2026 n=5591 net=-56898
| xvenue_funding_disloc | 370 | 202 | 0.530 | 0.479 | FAIL | 3177 | 0.54 | 0.792 | 0.014 | 0.060 | mixed | FAIL | **BLOCKED** |
  (power: n=370 (n_eff=316), Sharpe=0.54, MinTRL=634796d, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+24.0bp/ev t=2.41
  bb_p=0.179 (block=5)
  eras: 2024 n=117 net=-458 | 2025 n=118 net=+2570 | 2026 n=135 net=+1064
| xvenue_leadlag_1h | 793 | 0 | 0.444 | 0.410 | FAIL | -9537 | -4.75 | 0.000 | 0.000 | 0.268 | consistent | pass | **KILL** |
  (power: n=793 (n_eff=545), Sharpe=-4.75, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=-0.4bp/ev t=-0.13
  bb_p=0.000 (block=5)
  eras: 2026 n=793 net=-9537
| xvenue_basis_converge | 207 | 0 | 0.415 | 0.350 | FAIL | -3821 | -2.13 | 0.040 | 0.000 | 0.252 | consistent | pass | **KILL** |
  (power: n=207 (n_eff=57), Sharpe=-2.13, MinTRL=infd, MinBTL=20.7y@SR0.5)
  drift-audit: skill=+11.0bp/ev t=0.90
  bb_p=0.028 (block=5)
  eras: 2026 n=207 net=-3821
