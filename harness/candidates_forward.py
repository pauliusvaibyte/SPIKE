"""Forward-declared candidates — leads observed in-sample, declared
2026-09-23 and frozen at manifest `forward_declared.cutoff_utc`.

These wrap the killed/original implementations (or their declared
inverses) but are only evaluated on events with t >= CUTOFF. Pre-cutoff
events are emitted too (calibration context) — the RUNNER is responsible
for filtering to post-cutoff rows before verdict stats. Inverting a killed
family is admissible here ONLY because the declaration predates any
post-cutoff observation.
"""
from __future__ import annotations

import pandas as pd

from harness import candidates_round3 as C3
from harness import candidates_round4 as C4
from harness import candidates_round6 as C6
from harness import candidates_round9 as C9
from harness import candidates_round14 as C14
from harness.candidates import DEADBAND_BP, FEE_RT_BP

CUTOFF = pd.Timestamp("2026-09-23T00:00:00Z")
# Round-6 inverse leads were observed on data through ~08:40 UTC; their
# declaration cutoff is the first clean boundary after — 09:00Z.
CUTOFF_R6 = pd.Timestamp("2026-09-23T09:00:00Z")
# Round-8 leads derive from the flip decomposition run on data through
# ~10:00 UTC — next clean 4h boundary is 12:00Z.
CUTOFF_R8 = pd.Timestamp("2026-09-23T12:00:00Z")
# Round-10 flagship lead: declared on data through 2026-09-23; next clean
# daily boundary is 2026-09-24T00:00Z.
CUTOFF_R10 = pd.Timestamp("2026-09-24T00:00:00Z")

# Round-11 lead cutoff — nrpl anti-predictivity observed on data through
# 2026-09-23; forward set starts at the next clean daily boundary.
CUTOFF_R11 = pd.Timestamp("2026-09-24T00:00:00Z")

# Round-14 short leads — the WATCH autopsy + short-leg variants were
# evaluated on data through 2026-09-26 and declared 2026-09-28; the
# next clean daily boundary (whose lagged inputs publish strictly
# after the declaration) is 2026-09-29T00:00Z.
CUTOFF_R14 = pd.Timestamp("2026-09-29T00:00:00Z")

# Round-19 carry lead — the A29-override WATCH on funding_carry_24h was
# never forward-declared. Declared 2026-09-29; next clean daily boundary.
CUTOFF_R19 = pd.Timestamp("2026-09-30T00:00:00Z")

# Single source of truth for each declared lead's frozen cutoff — the
# runner partitions on it and the integrity verifier probes input
# freshness against it (a shared hardcoded date once false-FAILed the
# 09-23-declared leads against the 09-24 boundary).
LEAD_CUTOFFS = {
    "fwd_fng_fear_long": CUTOFF,
    "fwd_momentum_extremes": CUTOFF,
    "fwd_xvenue_disloc_cont": CUTOFF,
    "fwd_premium_cont": CUTOFF_R6,
    "fwd_funding_streak_fade": CUTOFF_R6,
    "fwd_alt_reversal": CUTOFF_R6,
    "fwd_mom24h_cont": CUTOFF_R8,
    "fwd_alt_resid_cont": CUTOFF_R8,
    "fwd_flagship_hlbtc": CUTOFF_R10,
    "fwd_nrpl_cont": CUTOFF_R11,
    "fwd_premium_basis_converge": CUTOFF_R11,
    "fwd_skew_reversal": CUTOFF_R11,
    "fwd_puell_extreme_cont": CUTOFF_R11,
    "fwd_reserve_risk_cont": CUTOFF_R11,
    "fwd_oi_divergence_short": CUTOFF_R14,
    "fwd_equity_lead_short": CUTOFF_R14,
    "fwd_riskoff_cluster": CUTOFF_R14,
    "fwd_dormancy_spike_long": CUTOFF_R14,
    "fwd_carry_p90_p10": CUTOFF_R19,
}

# Publish-lag accounting (2026-09-25 audit): external daily metrics are
# stamped for the day they describe but publish hours-to-days later
# (BGeometrics ~12:00Z next day, CoinMetrics capmvrvcur ~03:20Z next
# day, alternative.me fng ~00:0xZ same day). A signal evaluated at the
# modeled entry instant may only read rows already public then — the
# shift is applied inside each impl (he-frame leads enter at the daily
# close = ~00:00Z d+1 -> lag 1; round-4 leads enter at the ~00:00Z-d
# blockchain price -> lag 2; the flagship V leg already executes t+1 so
# one extra shift suffices). Machine check: the verifier re-runs each
# emitter with the lagged column's tail masked — emitted events must be
# identical, proving the signal cannot see unpublished rows.
LAGGED_INPUTS = {
    "fwd_fng_fear_long":       {"fng": 1},
    "fwd_momentum_extremes":   {"mvrv": 2},
    "fwd_flagship_hlbtc":      {"mvrv": 1},
    "fwd_nrpl_cont":           {"nrpl_usd": 1},
    "fwd_puell_extreme_cont":  {"puell": 1},
    "fwd_reserve_risk_cont":   {"reserve_risk": 1},
    "fwd_skew_reversal":       {"skew25_1m": 1},
    "fwd_oi_divergence_short": {"oi_binance": 2},
    "fwd_equity_lead_short":   {"fred_nasdaq": 1},
    "fwd_riskoff_cluster":     {"oi_binance": 2, "fred_nasdaq": 1},
    "fwd_dormancy_spike_long": {"dormancy": 1},
}

# Declared limiting inputs per lead — the single source both the runner
# (report labels) and tools/verify_integrity (freshness gate) evaluate
# via D.forward_input_probes(). spec = (label, [(src, arg), ...]); the
# lead's probe is the MIN over its specs' last-valid timestamps — a lead
# only accrues when every input in its spec is fresh enough to cross its
# cutoff. src vocabulary is evaluated in harness/data.py:
#   ("macro", [cols])            harmony_daily columns
#   ("hext",  [cols])            harmony_extended columns
#   ("hl_funding", "all")        HL funding_full, min over assets
#   ("bn_funding", "all")        Binance funding, min over assets
#   ("candles", ("all"|a, iv))   HL candles_full, min over assets or one
#   ("bn_klines", ("all"|a,iv))  Binance klines
#   ("bn_premium", "all")        Binance premiumIndexKlines 1d
LEAD_INPUT_SPECS = {
    "fwd_fng_fear_long": ("macro.fng+c",
                        [("macro", ["fng", "c"])]),
    "fwd_momentum_extremes": ("macro.mvrv+c",
                             [("macro", ["mvrv", "c"])]),
    "fwd_xvenue_disloc_cont": ("HL+BN funding+4h",
        [("hl_funding", "all"), ("bn_funding", "all"),
         ("candles", ("all", "4h"))]),
    "fwd_premium_cont": ("HL funding+4h",
        [("hl_funding", "all"), ("candles", ("all", "4h"))]),
    "fwd_funding_streak_fade": ("HL funding+4h",
        [("hl_funding", "all"), ("candles", ("all", "4h"))]),
    "fwd_alt_reversal": ("1h candles", [("candles", ("all", "1h"))]),
    "fwd_mom24h_cont": ("4h candles", [("candles", ("all", "4h"))]),
    "fwd_alt_resid_cont": ("1d candles", [("candles", ("all", "1d"))]),
    "fwd_flagship_hlbtc": ("1d BTC+macro.mvrv",
        [("candles", ("btc", "1d")), ("macro", ["mvrv"])]),
    "fwd_nrpl_cont": ("nrpl_usd+px_bitstamp",
        [("hext", ["nrpl_usd", "px_bitstamp"])]),
    "fwd_premium_basis_converge": ("BN premium+klines 1d",
        [("bn_premium", "all"), ("bn_klines", ("all", "1d"))]),
    "fwd_skew_reversal": ("skew25_1m+px_bitstamp",
        [("hext", ["skew25_1m", "px_bitstamp"])]),
    "fwd_puell_extreme_cont": ("puell+px_bitstamp",
        [("hext", ["puell", "px_bitstamp"])]),
    "fwd_reserve_risk_cont": ("reserve_risk+px_bitstamp",
        [("hext", ["reserve_risk", "px_bitstamp"])]),
    "fwd_oi_divergence_short": ("macro.oi+c",
        [("macro", ["oi_binance", "c"])]),
    "fwd_equity_lead_short": ("macro.nasdaq+c",
        [("macro", ["fred_nasdaq", "c"])]),
    "fwd_riskoff_cluster": ("macro.oi+nasdaq+c",
        [("macro", ["oi_binance", "fred_nasdaq", "c"])]),
    "fwd_dormancy_spike_long": ("hext.dormancy+px_bitstamp",
        [("hext", ["dormancy", "px_bitstamp"])]),
    "fwd_carry_p90_p10": ("HL funding+4h",
        [("hl_funding", "all"), ("candles", ("all", "4h"))]),
}

# Per-lead drift-skill price frames — the same clocks the leads eval on.
# spec: ("macro"|"hext"|("candles",(asset,iv))|("candles_dict",iv)|
#        ("prem_dict",)). Evaluated by D.forward_drift_prices() so the
# runner's report and the verifier's recomputation use identical frames.
LEAD_DRIFT_SPECS = {
    "fwd_fng_fear_long": ("macro", None),
    "fwd_momentum_extremes": ("macro", None),
    "fwd_xvenue_disloc_cont": ("candles_dict", "4h"),
    "fwd_premium_cont": ("candles_dict", "4h"),
    "fwd_funding_streak_fade": ("candles_dict", "4h"),
    "fwd_alt_reversal": ("candles_dict", "1h"),
    "fwd_mom24h_cont": ("candles_dict", "4h"),
    "fwd_alt_resid_cont": ("candles_dict", "1d"),
    "fwd_flagship_hlbtc": ("candles", ("btc", "1d")),
    "fwd_nrpl_cont": ("hext", None),
    "fwd_premium_basis_converge": ("prem_dict", None),
    "fwd_skew_reversal": ("hext", None),
    "fwd_puell_extreme_cont": ("hext", None),
    "fwd_reserve_risk_cont": ("hext", None),
    "fwd_oi_divergence_short": ("macro", None),
    "fwd_equity_lead_short": ("macro", None),
    "fwd_riskoff_cluster": ("macro", None),
    "fwd_dormancy_spike_long": ("hext", None),
    "fwd_carry_p90_p10": ("candles_dict", "4h"),
}


def retired_leads() -> dict:
    """manifest.forward_retired: leads whose limiting input went extinct
    UPSTREAM (not a SPIKE lag). The declaration stays frozen and keeps
    being evaluated — retirement only changes how a dead input is
    reported (RETIRED, visible WARN) instead of an eternal FAIL. Provider
    substitution is forbidden, so this is the only honest terminal state.
    A retired lead whose input revives is flagged for review."""
    from pathlib import Path
    import yaml
    p = Path(__file__).resolve().parent.parent / "manifest.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {r["lead"]: r for r in (doc.get("forward_retired") or [])}


def _invert(ev: pd.DataFrame) -> pd.DataFrame:
    """Flip direction; negate gross, keep the same fee off the new gross.
    hit uses the contract convention (gross > DEADBAND_BP), NOT net>0 —
    the net>0 variant failed validate_events on every inverted file."""
    fee = ev["gross_bp"] - ev["ret_bp"]
    ev = ev.copy()
    ev["dir"] = -ev["dir"]
    ev["gross_bp"] = -ev["gross_bp"]
    ev["ret_bp"] = ev["gross_bp"] - fee
    ev["hit"] = ev["gross_bp"] > DEADBAND_BP
    return ev


def fwd_fng_fear_long(df: pd.DataFrame) -> pd.DataFrame:
    """fng <= 10 -> LONG 7d. Fear-only side of fng_extreme_sentiment."""
    ev = C4.fng_extreme_sentiment(df)
    return ev[ev["dir"] > 0].reset_index(drop=True) if not ev.empty else ev


def fwd_momentum_extremes(df: pd.DataFrame) -> pd.DataFrame:
    """mvrv 730d-pctile extremes -> WITH momentum: high -> LONG, low -> SHORT.
    Declared inverse of the killed contrarian onchain_mvrv_regime."""
    ev = C4.onchain_mvrv_regime(df)
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


def fwd_xvenue_disloc_cont(hl_fund: pd.DataFrame, bn_fund: pd.DataFrame,
                           bars4h: pd.DataFrame, asset: str) -> pd.DataFrame:
    """Continuation direction of the killed fade: dir = +sign(spread)."""
    ev = C3.xvenue_funding_disloc(hl_fund, bn_fund, bars4h, asset)
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


# ── Round-6 inverse leads (cutoff CUTOFF_R6) ─────────────────────────────

def fwd_premium_cont(fund: pd.DataFrame, bars4h: pd.DataFrame,
                     asset: str) -> pd.DataFrame:
    """Premium sign CONTINUES at +8h — inverse of killed hl_premium_disloc
    (in-sample: fade won .442 => continuation ~.558 gross)."""
    ev = C6.hl_premium_disloc(fund, bars4h, asset)
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


def fwd_funding_streak_fade(fund: pd.DataFrame, bars4h: pd.DataFrame,
                            asset: str) -> pd.DataFrame:
    """Fade >=24h same-sign funding streaks — inverse of killed
    funding_run_persistence (in-sample: continuation won .413 => fade
    ~.587 gross)."""
    ev = C6.funding_run_persistence(fund, bars4h, asset)
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


def fwd_alt_reversal(btc_bars: pd.DataFrame, alt_bars: pd.DataFrame,
                     asset: str) -> pd.DataFrame:
    """Alt reverses a large BTC 1h move — inverse of killed
    xasset_btc_leads_alts (in-sample: continuation won .446 => reversal
    ~.554 gross)."""
    ev = C6.xasset_btc_leads_alts(btc_bars, alt_bars, asset)
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


# ── Round-8 leads (cutoff CUTOFF_R8) ─────────────────────────────────────

def fwd_mom24h_cont(bars4h: pd.DataFrame, asset: str,
                    horizon_bars: int = 6) -> pd.DataFrame:
    """24h momentum continuation — the mechanism isolated by the
    funding_flip decomposition (aligned flips hit .614, counter .426).
    Non-overlapping events: every 6 bars, dir=sign(24h ret), eval next 6."""
    import numpy as np
    c = bars4h["c"].to_numpy(dtype=float)
    t = bars4h["t"]
    rows, i = [], 6
    while i < len(c):
        ret24 = c[i] / c[i - 6] - 1.0
        if np.isfinite(ret24) and ret24 != 0 and c[i] > 0:
            d = 1.0 if ret24 > 0 else -1.0
            if i + horizon_bars > len(c) - 1:
                rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                             "t_eval": t.iloc[i], "ret_bp": float("nan"),
                             "gross_bp": float("nan"),
                             "exit_reason": "uncovered"})
            elif not (np.isfinite(c[i + horizon_bars])
                      and c[i + horizon_bars] > 0):
                rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                             "t_eval": t.iloc[i], "ret_bp": float("nan"),
                             "gross_bp": float("nan"),
                             "exit_reason": "uncovered"})
            else:
                g = d * (c[i + horizon_bars] / c[i] - 1.0) * 1e4
                rows.append({"t": t.iloc[i], "asset": asset, "dir": d,
                             "t_eval": t.iloc[i + horizon_bars],
                             "ret_bp": g - FEE_RT_BP, "gross_bp": g})
            i += horizon_bars
        else:
            i += 1
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["hit"] = df["gross_bp"] > 1.0
    return df


def fwd_alt_resid_cont(btc_d: pd.DataFrame, alt_d: pd.DataFrame,
                       asset: str) -> pd.DataFrame:
    """Alt residual moves CONTINUE +1d — inverse of killed
    alt_resid_reversal_1d (in-sample: fade won .461 => cont ~.539 gross)."""
    from harness import candidates_round8 as C8
    ev = C8.alt_resid_reversal_1d(btc_d, alt_d, asset)
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


# ── Round-10 lead (cutoff CUTOFF_R10) ────────────────────────────────────

def fwd_flagship_hlbtc(bars1d: pd.DataFrame, mvrv: pd.Series
                     ) -> pd.DataFrame:
    """s45125 base + V brake (mvrv>2.5 -> x0.75) on HL BTC daily.
    N-leg excluded — declared spec is base+V (CM flows ARE refreshed
    daily now via refresh_aux_sources, but adding the leg would change
    the frozen forward spec — kept as declared).
    Events = invested days (continuous-position event frame)."""
    from harness import candidates_round10 as C10
    df = bars1d[["t", "c"]].copy()
    if getattr(df["t"].dt, "tz", None) is not None:
        df["t"] = df["t"].dt.tz_convert(None)
    px = df.set_index("t")["c"].astype(float)
    w = C10.w_base(px)
    # capmvrvcur[d-1] finalizes ~03:20Z day d, ~3h AFTER the modeled
    # w[i-1] execution at the bar-(i-1) close (~00:00Z i) — one extra day
    # keeps the V brake on provably-published values (publish-lag audit)
    mv = mvrv.reindex(px.index).ffill().shift(1)
    w = w * (1 - 0.25 * (mv > 2.5).astype(float))
    return C10.position_events(df, w, "BTC")


# ── Round-11 lead (cutoff CUTOFF_R11) ────────────────────────────────────

def fwd_nrpl_cont(he: pd.DataFrame) -> pd.DataFrame:
    """nrpl_usd >= prior p90 -> LONG +3d — inverse of killed
    nrpl_spike_top_3d (in-sample: SHORT hit .401, net -77431bp, bb_p<.001
    => LONG continuation ~.599 gross implied on n=317, era-consistent).
    he = harmony_extended frame with c = px_bitstamp."""
    from harness import candidates_round11 as C11
    ev = C11.nrpl_spike_top_3d(he, "BTC")
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


def fwd_premium_basis_converge(prem_merged: pd.DataFrame, asset: str
                             ) -> pd.DataFrame:
    """Same direction as the WATCH — |premiumIndex| >= prior p90 ->
    dir=-sign(premium), +1d. Drift-audit showed symmetric non-beta skill
    (+26.7bp/ev, L +26.6 / S +26.9) on n=1044; forward accrual is the
    honest arbiter. prem_merged: t/c (perp close) + prem (index close)."""
    from harness import candidates_round11 as C11
    return C11.premium_basis_converge_1d(prem_merged, asset)


def fwd_skew_reversal(he: pd.DataFrame) -> pd.DataFrame:
    """Same direction as the WATCH — skew25_1m <= p10 -> LONG +3d,
    >= p90 -> SHORT +3d. Drift-audit: +50.9bp/ev skill, symmetric
    (L +45 / S +59) but n=114 — needs post-cutoff proof."""
    from harness import candidates_round11 as C11
    return C11.skew_extreme_reversal_3d(he, "BTC")


# ── Round-12 leads (cutoff CUTOFF_R11 — same 09-24 boundary) ───────────

def fwd_puell_extreme_cont(he: pd.DataFrame) -> pd.DataFrame:
    """INVERSE of killed puell_extreme_7d: puell >= p90 -> LONG +7d,
    <= p10 -> SHORT +7d (miner extremes CONTINUE, not revert).
    In-sample: declared side -69804bp, skill t=-3.15, symmetric."""
    from harness import candidates_round12 as C12
    ev = C12.puell_extreme_7d(he, "BTC")
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


def fwd_reserve_risk_cont(he: pd.DataFrame) -> pd.DataFrame:
    """INVERSE of killed reserve_risk_regime_7d: reserve_risk <= p10 ->
    SHORT +7d, >= p90 -> LONG +7d (valuation regimes trend).
    In-sample: declared side -72131bp, skill t=-3.63, symmetric."""
    from harness import candidates_round12 as C12
    ev = C12.reserve_risk_regime_7d(he, "BTC")
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev


# ── Round-14 leads (cutoff CUTOFF_R14 — 2026-09-29 boundary) ──────────
# Same-direction declarations on the round-14 short-side variants: the
# WATCH autopsy showed the parents' skill concentrated short-side, and
# the in-sample variants carry t_skill ~3 but fail the hit-rate gate
# (magnitude payoffs, ~52% episode wins). Declared so the post-cutoff
# stream can accrue power independent of the in-sample verdict.

def fwd_oi_divergence_short(df: pd.DataFrame) -> pd.DataFrame:
    """Short leg of oi_price_divergence (oi 20d-z decile vs ret 20d
    decile >= 7 apart, oi rising vs px falling) -> SHORT 5d.
    In-sample variant: n_ep=40, skill +243bp/ep t=0.97."""
    return C14.oi_price_divergence_short(df)


def fwd_equity_lead_short(df: pd.DataFrame) -> pd.DataFrame:
    """Short leg of equity_lead_btc_5d (nasdaq 5d z <= -2, eq drop vs
    BTC flat) -> SHORT 5d. In-sample variant: n_ep=121,
    skill +240bp/ep t=3.04."""
    return C14.equity_lead_btc_5d_short(df)


def fwd_riskoff_cluster(df: pd.DataFrame) -> pd.DataFrame:
    """Union of the two short triggers above — does clustering add
    power? In-sample: n_ep=149, skill +276bp/ep t=3.09 but diluted
    net vs the equity-lead single (8238 vs 10960)."""
    return C14.riskoff_cluster_5d(df)


def fwd_carry_p90_p10(fund: pd.DataFrame, bars4h: pd.DataFrame,
                      asset: str) -> pd.DataFrame:
    """Funding-carry WATCH forward: rate >= rolling-1y-p90 -> SHORT
    (collect); <= p10 -> LONG (collect); hold 24h; gross = dir*px_ret +
    (-dir)*sum(next 24 realized rates). SAME direction as the A29
    override-restored funding_carry_24h WATCH (the killed q=0.05 extreme
    variant is NOT declared). Carry income, not price prediction."""
    return C9.funding_carry_24h(fund, bars4h, asset, q=0.10)


def fwd_dormancy_spike_long(he: pd.DataFrame) -> pd.DataFrame:
    """INVERSE of killed round-15 dormancy_spike_short_7d: dormancy
    >= prior p90 -> LONG +7d. Declared side lost -87133bp across
    287 events (Sharpe -2.91, bb_p=0.001, consistent across eras) —
    old-coin distribution spikes mark UPSIDE continuation, not
    overhang. Inverse implied ~+81k bp."""
    from harness import candidates_round15 as C15
    ev = C15.dormancy_spike_short_7d(he, "BTC")
    return _invert(ev).reset_index(drop=True) if not ev.empty else ev
