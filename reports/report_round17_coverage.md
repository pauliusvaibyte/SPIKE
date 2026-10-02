# Phase -1 Round 17 — new-mechanism coverage audit (commissioned 2026-09-29)

Commissioned question: does any **genuinely new, powered mechanism** remain
evaluable on owned data? Answer: **no.** Every data feed present has already
powered at least one family evaluation; the only literally-untouched inputs
are underpowered by construction. Running them would produce noise verdicts,
which the power doctrine forbids interpreting.

## Feed inventory vs family claims

| Feed | Depth | Families billed | Status |
|---|---|---|---|
| candles 1d/4h/1h/15m (7 assets) | ~3.3y / 833d | TREND-1/2, MRV, FLUSH-1, VOL-REGIME, VOL-SHOCK, VOLUME-CLIMAX, SESSION x3, BREADTH, RESID-REV, CAPITULATION, MICRO-BOUNCE, CAL-REBAL, weekend | all evaluated; WATCHes decayed |
| HL funding_full (28.9k rows x2+) | ~3.3y | FRA, FRA-CHALLENGER, CARRY, FUNDING-FLIP, FUNDING-DURATION | all KILL (carry WATCH->decayed) |
| Binance funding/klines/premium (7) | ~2y | BASIS-1, MARK-DISLOC, xvenue x3, TOXIC-FLOW | all KILL |
| Binance OI 1h + taker_ls (623r) | ~26d | OI-CROWD, TOXIC-FLOW | powered retest on deeper klines: KILL |
| harmony macro_daily (5488 cols screened) | 2010-2026 | ONCHAIN family cluster (MVRV/NRPL/SOPR/Puell/reserve/dormancy/LTH-SOPR), MACRO-BETA, MACRO-VOL, FNG, ETF, OI-DIVERGENCE | KILL/anti-predictive; inverses forward-accruing |
| coinmetrics_daily | daily | consumed via harmony pipeline | same |
| grok l2_journal | 445 rows | OFI | evaluated (short window) |
| grok liq_journal | **173 hourly rows** | none | **unpowerable** (~7d) |
| grok oi_journal (mainnet+testnet) | <=4k rows, days | none | **unpowerable** |

## Screen-factor disposition (harmony_screen, 5488 cols)

All four confirmed factors resolve without a new evaluable family:

- **Valuation-level mean reversion** — dominant factor, overlaps killed trend/MR families.
- **OI level -> 21d reversion** (ic -0.25/-0.30, 3 sources) — already
  screen-validated incl. >=2025 holdout; a dedicated tradeable-spec eval on
  ~1400 daily rows yields ~60 non-overlapping 21d events -> underpowered.
  Correct path is the existing fwd_ pipeline, not re-eval.
- **Coinbase premium** — BLOCKED (leak, corr .97 vs next-day ret); live
  CryptoQuant columns exist but are masked-lookahead pending clean feed.
- **Small-holder cohorts** — the only screened-but-never-dedicated-eval
  series, but same on-chain-daily mechanism class as 6+ powered KILLs; an
  in-sample eval would double-dip the screen. Forward-declare or nothing.

## Verdict census (manifest, 2026-09-29)

52 declared families, ~136 recorded evaluations. Powered real candidates:
all KILL or WATCH-decayed; **zero promotion-ready survivors**. The 18
declared `fwd_*` leads are the live forward-evidence surface — untouched
by in-sample evaluation and accruing by design.

## Unlock paths (what would actually open new families)

1. **HL-native OI + liquidation history** — grok journals are accruing
   mainnet OI and testnet liq already; months to powered depth. Genuine
   new domain (forced-flow/positioning), not a mutation.
2. **Options skew / DVOL** — ~~no options feed owned~~ **ERRATUM
   (2026-09-29)**: harmony_extended already carries `dvol_close`
   (n=2014), ATM IV x4 tenors, skew25 x3 — stale (ends 2026-02-19) but
   evaluated in round 11 (dvol_spike_bounce KILL; skew/iv WATCH).
   Deribit adds provider-native provenance and freshness continuation —
   an extended-history surface, not a new domain.
3. **Cross-venue orderbook depth time-series** — depth asymmetry, not
   imbalance snapshots; needs months of accrual or a paid feed.
4. **HL premium-index long history** — basis mechanism on venue-native
   series (current BASIS-1 used Binance-derived premium).

## Conclusion

The owned-data mechanism space is exhausted at declared power. Further
evaluations on existing feeds would be multiplicity burn — same families
under new names. The correct research posture is the one already in
place: forward leads accrue untouched, journals deepen toward power, and
a new family is registered only when a new *data domain* or an ex-ante
mechanism with no family overlap exists. Program closure stands.
