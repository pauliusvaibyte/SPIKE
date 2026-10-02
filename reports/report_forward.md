# Forward evaluation — declared 2026-09-23, cutoff-frozen

data-as-of: macro.mvrv+c=2026-09-30; 1d BTC+macro.mvrv=2026-09-30; nrpl_usd+px_bitstamp=2026-09-29

Cutoffs: 2026-09-23 00:00:00+00:00 (round-1) / 2026-09-23 09:00:00+00:00 (round-6 inverses) / 2026-09-23 12:00:00+00:00 (round-8 decomposition leads) / 2026-09-24 00:00:00+00:00 (round-10 flagship shadow) / 2026-09-24 00:00:00+00:00 (round-11 nrpl inverse). Only post-cutoff events enter stats.

## fwd_fng_fear_long
premise: MIXED — IS fear side +14k/.615 but replay direction flips across cutoffs (unstable)
post-cutoff: n=0 n_eff=0 hit=nan wilson_lo=nan net=+0bp drift_t=nan -> **ACCRUING**
(pre-cutoff context events: 26 — excluded by design)

## fwd_momentum_extremes
premise: INTACT — inverse of killed mvrv_regime
post-cutoff: n=0 n_eff=0 hit=nan wilson_lo=nan net=+0bp drift_t=nan -> **ACCRUING**
(pre-cutoff context events: 91 — excluded by design)

## fwd_xvenue_disloc_cont
premise: SUSPECT — in-sample disloc now BLOCKED (boundary-invariance fails once aux frames truncate, A24); implied cont ~.467 post-fix, was .623
post-cutoff: n=21 n_eff=12 hit=0.667 wilson_lo=0.391 net=-2414bp drift_t=-0.46 -> **ACCRUING**
(pre-cutoff context events: 1952 — excluded by design)
  eras: 2026 n=21 net=-2414

## fwd_premium_cont
premise: WEAK — hl_premium_disloc fully clean: .495, -135.6k; implied continuation ~coin flip (was .558)
post-cutoff: n=48 n_eff=12 hit=0.250 wilson_lo=0.089 net=-2935bp drift_t=-2.16 -> **ACCRUING**
(pre-cutoff context events: 9502 — excluded by design)
  eras: 2026 n=48 net=-2935

## fwd_funding_streak_fade
premise: VOID — funding_run_persistence clean is .498; nothing to fade
post-cutoff: n=6 n_eff=4 hit=0.500 wilson_lo=0.150 net=-526bp drift_t=-0.51 -> **ACCRUING**
(pre-cutoff context events: 1287 — excluded by design)
  eras: 2026 n=6 net=-526

## fwd_alt_reversal
premise: INTACT — xasset_btc_leads_alts still anti-predictive (.447 KILL) post-fix
post-cutoff: n=126 n_eff=21 hit=0.619 wilson_lo=0.409 net=-2351bp drift_t=-0.44 -> **ACCRUING**
(pre-cutoff context events: 2100 — excluded by design)
  eras: 2026 n=126 net=-2351

## fwd_mom24h_cont
premise: NEGATIVE — round13 replay: OOS negative at all 3 Binance cutoffs (HL pool still accrues; venue caveat)
post-cutoff: n=49 n_eff=1 hit=0.000 wilson_lo=0.000 net=-7275bp drift_t=-inf -> **ACCRUING**
(pre-cutoff context events: 5830 — excluded by design)
  eras: 2026 n=49 net=-7275

## fwd_alt_resid_cont
premise: INTACT — alt_resid_reversal still anti-predictive (.463 KILL) post-fix
post-cutoff: n=7 n_eff=4 hit=0.250 wilson_lo=0.046 net=-904bp drift_t=-0.63 -> **ACCRUING**
(pre-cutoff context events: 466 — excluded by design)
  eras: 2026 n=7 net=-904

## fwd_flagship_hlbtc
premise: STRONG — walk-forward transfer at all 4 cutoffs, DSR >= .995
post-cutoff: n=7 n_eff=1 hit=0.000 wilson_lo=0.000 net=-90bp drift_t=-inf -> **ACCRUING**
(pre-cutoff context events: 774 — excluded by design)
  eras: 2026 n=7 net=-90

## fwd_nrpl_cont
premise: STRONG — replay: direction re-derives at all 4 cutoffs, OOS positive every time
post-cutoff: n=0 n_eff=0 hit=nan wilson_lo=nan net=+0bp drift_t=nan -> **ACCRUING**
(pre-cutoff context events: 316 — excluded by design)

## fwd_premium_basis_converge
premise: INTACT — same-direction WATCH; mature-selection transfer in replay
post-cutoff: n=3 n_eff=1 hit=0.000 wilson_lo=0.000 net=-166bp drift_t=-inf -> **ACCRUING**
(pre-cutoff context events: 1045 — excluded by design)
  eras: 2026 n=3 net=-166

## fwd_skew_reversal
premise: INTACT-THIN — revert re-derives at viable cutoffs; input dead upstream
post-cutoff: **RETIRED** — input 'skew25_1m+px_bitstamp' extinct upstream (last valid 2026-02-19 00:00Z; ledger A28); substitution forbidden, declaration kept frozen and re-evaluated daily — flags if the source revives

## fwd_puell_extreme_cont
premise: STRONG — replay: cont re-derives at all 4 cutoffs
post-cutoff: n=0 n_eff=0 hit=nan wilson_lo=nan net=+0bp drift_t=nan -> **ACCRUING**
(pre-cutoff context events: 334 — excluded by design)

## fwd_reserve_risk_cont
premise: DECAYING — replay OOS positive but thinning; input dead upstream
post-cutoff: **RETIRED** — input 'reserve_risk+px_bitstamp' extinct upstream (last valid 2025-12-28 00:00Z; ledger A28); substitution forbidden, declaration kept frozen and re-evaluated daily — flags if the source revives

## fwd_oi_divergence_short
premise: WATCH-BASIS — round-14 short variant: +243bp/ep t=0.97, ep-gate fail on n=40
post-cutoff: n=0 n_eff=0 hit=nan wilson_lo=nan net=+0bp drift_t=nan -> **ACCRUING**
(pre-cutoff context events: 40 — excluded by design)

## fwd_equity_lead_short
premise: STRONG-SKILL — round-14: +240bp/ep t=3.04; magnitude edge, hit-rate gate can't bless IS
post-cutoff: **AWAITING** — input 'macro.nasdaq+c' last valid 2026-09-28 00:00Z < cutoff 2026-09-29 00:00Z but still publishing; first crossing on the next input cycle (auto-resumes; nothing is lost)

## fwd_riskoff_cluster
premise: DILUTED — round-14: +276bp/ep t=3.09 but net < equity-lead single (shared risk-off state)
post-cutoff: **AWAITING** — input 'macro.oi+nasdaq+c' last valid 2026-09-28 00:00Z < cutoff 2026-09-29 00:00Z but still publishing; first crossing on the next input cycle (auto-resumes; nothing is lost)

## fwd_dormancy_spike_long
premise: STRONG-INVERSE — round-15 declared side lost -87133bp (bb_p=0.001, era-consistent); anti-predictive like nrpl/puell inverses
post-cutoff: **AWAITING** — input 'hext.dormancy+px_bitstamp' last valid 2026-09-26 00:00Z < cutoff 2026-09-29 00:00Z but still publishing; first crossing on the next input cycle (auto-resumes; nothing is lost)

## fwd_carry_p90_p10
premise: WATCH-BASIS — A29 override-restored carry WATCH: +13.7bp/ev drift skill (t=1.93), income mechanism not beta; forward accrual decides if the WATCH earns a forward gate
post-cutoff: n=2 n_eff=1 hit=0.000 wilson_lo=0.000 net=-181bp drift_t=-inf -> **ACCRUING**
(pre-cutoff context events: 4255 — excluded by design)
  eras: 2026 n=2 net=-181


# Diagnostic battery — all event streams, post 2026-09-24
(diagnostic only — revival here is a NEW hypothesis, not a promotion)

- basis1_premium_p10: n=5 hit=0.800 net=+245bp
- flagship_base_alts: n=42 hit=0.548 net=+2630bp **WATCHING**
- flagship_base_btc: n=7 hit=0.286 net=-101bp
- flagship_composite_alts: n=42 hit=0.548 net=+2630bp **WATCHING**
- flagship_composite_bnbtc: n=7 hit=0.571 net=-92bp
- flagship_composite_btc: n=7 hit=0.286 net=-101bp
- flagship_composite_hlbtc: n=7 hit=0.571 net=-90bp
- premium_basis_converge_1d: n=3 hit=0.333 net=-166bp
- funding_carry_extreme: n=41 hit=0.390 net=-4406bp
- us10y_shock_short_5d: n=1 hit=nan net=+47bp
- basis1_premium_p10_enriched: n=2 hit=1.000 net=+151bp
- settle1_funding_drift: n=241 hit=0.498 net=-2372bp
- xvenue_funding_disloc: n=6 hit=0.333 net=+99bp
- xvenue_leadlag_1h: n=47 hit=0.362 net=-991bp
- cal_weekend_drift: n=1 hit=nan net=-75bp
- funding_run_persistence: n=6 hit=0.667 net=+406bp
- funding_xasset_rv: n=17 hit=0.647 net=+1285bp
- hl_premium_disloc: n=45 hit=0.644 net=+966bp **WATCHING**
- serialcorr_15m_bounce: n=584 hit=0.560 net=-3733bp
- taker_toxicity_1h: n=42 hit=0.524 net=-374bp
- xasset_btc_leads_alts: n=114 hit=0.395 net=-854bp
- alt_resid_reversal_1d: n=7 hit=0.714 net=+764bp
- funding_flip_momentum: n=28 hit=0.429 net=-336bp
- rsi2_connors_1d: n=11 hit=0.455 net=+629bp
- rv_spike_fade_4h: n=5 hit=0.400 net=-890bp
- taker_share_fade_1h: n=93 hit=0.538 net=-635bp
- trapped_positioning_squeeze: n=9 hit=0.333 net=-2502bp
- volume_climax_fade: n=5 hit=0.600 net=-346bp
- asia_session_drift: n=49 hit=0.429 net=-1474bp
- breadth_thrust_1d: n=14 hit=0.714 net=+1648bp
- btc_alt_rotation_3d: n=2 hit=0.500 net=-588bp
- compression_breakout_4h: n=1 hit=nan net=-149bp
- funding_carry_24h: n=41 hit=0.439 net=-3677bp
- us_session_drift: n=49 hit=0.408 net=-505bp
- us_session_momentum: n=41 hit=0.439 net=-510bp
(tracking 88 streams; 35 with post-boundary events)
