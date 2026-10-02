# Phase -1 Round 2 — extended-data evaluation

data: `data_extended/` — fundingHistory backfilled to launch (28,894 rows,
Jun 2023 -> Sep 2026) x 4h eval bars (833d, Jun 2024 -> Sep 2026).
Specs frozen; only data depth changed (declared collect_only re-test).
Eval granularity note: 4h-bar exit paths are coarser than live 5-min
mids — conservative bias on SL/TP resolution (errata E5).

| candidate | n | hit | wilson_lo | gate | net_bp | Sharpe | PSR | DSR | placebo_p | splits | leak | **verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fra_momentum_p90_long | 137 | 0.474 | 0.393 | FAIL | -3413 | -0.98 | 0.066 | 0.000 | 0.438 | mixed | FAIL | **BLOCKED** |
  (n_uncovered=1068, power: n=137 (n_eff=137), Sharpe=-0.98, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.112 (block=5)
  eras: 2024 n=61 net=+84 | 2025 n=54 net=-3144 | 2026 n=22 net=-353
| fra_momentum_p90_long_r3000 | 122 | 0.484 | 0.397 | FAIL | -1511 | -0.43 | 0.256 | 0.000 | 0.907 | mixed | FAIL | **BLOCKED** |
  (n_uncovered=1059, power: n=122 (n_eff=122), Sharpe=-0.43, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.293 (block=5)
  eras: 2024 n=59 net=+871 | 2025 n=55 net=-2305 | 2026 n=8 net=-78
| fra_fade_p90_short | 299 | 0.478 | 0.422 | FAIL | -7765 | -1.08 | 0.043 | 0.000 | 0.435 | consistent | FAIL | **BLOCKED** |
  (n_uncovered=2067, power: n=299 (n_eff=149), Sharpe=-1.08, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.079 (block=5)
  eras: 2024 n=133 net=-4551 | 2025 n=95 net=-1802 | 2026 n=71 net=-1412
| basis1_premium_p10 | 609 | 0.553 | 0.514 | PASS | 3817 | 0.43 | 0.742 | 0.020 | 0.039 | consistent | FAIL | **BLOCKED** |
  (n_uncovered=293, power: n=609 (n_eff=264), Sharpe=0.43, MinTRL=infd, MinBTL=20.7y@SR0.5)
  bb_p=0.255 (block=5)
  eras: 2024 n=167 net=-141 | 2025 n=278 net=+3705 | 2026 n=164 net=+253
