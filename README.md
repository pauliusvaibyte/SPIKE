# SPIKE — falsification harness for crypto trading theses

A pre-registration-first quantitative research harness for testing trading
hypotheses on Hyperliquid / Binance / Deribit / on-chain data, built to make
it *hard to fool yourself*: every hypothesis is declared in `manifest.yaml`
before execution, billed to a mechanism family for multiplicity accounting,
and gated on power / placebo / drift / cluster-concentration checks.

## Result of the program (2025-09 → 2026-09)

**52 mechanism families, ~85 evaluations, ~3.3y multi-venue data → zero
tradeable survivors.** Declared falsified-complete 2026-09-30 (see
`manifest.yaml` + `reports/`). Published as a worked example of doing
trading research honestly: every kill, override, erratum, and the full
event-level evidence corpus is in the repo.

## Layout

- `manifest.yaml` — the trial ledger: every hypothesis, family billing,
  verdict, override, forward declaration
- `harness/` — candidate emitters (`candidates_round*.py`,
  `candidates_forward.py`), loaders (`data.py`), gate math (`falsify.py`)
- `run_*.py` — reproducible round runners (each regenerates its report)
- `run_forward_eval.py` — forward-lead evaluator: post-cutoff events only
- `tools/verify_integrity.py` — corpus verifier (contracts, anchoring,
  power-gate invariants, publish-lag invariance, manifest↔artifact checks)
- `tools/morning_research.py` — daily pipeline: refresh → evals → verify
- `tools/collect_live.py`, `tools/backfill_*.py` — data acquisition
- `reports/` — all evidence: per-round reports + `events_*.csv` streams
  + `report_forward.md` + morning notes + integrity journals
- `AGENTS.md`, `DATA_SOURCES.md`,
  `QUANTLAB_OS_MASTER_ENGINEERING_SPEC.md` — doctrine and specs

## Regenerating data

`data_extended/` is gitignored (80M of public market data). Rebuild:

```
python tools/backfill_funding.py   # Hyperliquid funding history
python tools/backfill_candles.py   # HL candles 15m/1h/4h/1d
python tools/backfill_binance.py   # funding, klines, OI, taker flow
python tools/backfill_deribit.py   # DVOL + third-venue funding
python tools/collect_live.py       # live accrual (run hourly for depth/OI)
```

Then any `run_roundN.py` reproduces its report; `run_forward_eval.py`
rebuilds the forward surface; `tools/verify_integrity.py` checks the corpus.

## Caveats

- Signals are research artifacts, not trading advice. Every powered
  candidate in this corpus failed its gates — that is the finding.
- `harmony_*`/`coinmetrics` inputs came from community APIs that silently
  revise history; in-sample results on them carry that caveat (journaled
  in `reports/coverage_journal.md`).
- Forward leads declared but left accruing at closure live under
  `manifest.forward_declared*` — they resume evaluation the moment the
  pipeline is run again.
