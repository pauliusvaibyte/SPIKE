# Phase -1 Round 19 — §87 exit-path faithfulness bounds

Declared in manifest `round19_exitpath_check` (BILLED to FRA).
Round-2's r3000 kill already used the spec payout (4%/8%/3%/24h);
this bounds the residual 4h intra-bar ordering ambiguity.
reconcile vs saved r3000 events (covered n): MATCH

## SL-first (round-2 convention)
n=122  hit=0.484  net=-1511bp  Sharpe=-0.43  DSR=0.000
exits: {'time': 106, 'sl': 14, 'trail': 2}

## TP-first (optimistic bound)
n=122  hit=0.484  net=-1511bp  Sharpe=-0.43  DSR=0.000
exits: {'time': 106, 'sl': 14, 'trail': 2}

**VERDICT: TRANSFERS — net <= 0 under both intra-bar orderings; the §87 thesis is dead in its own payout shape, not just as a forward-return approximation. Live shadow remains prospective-confirmation only.**