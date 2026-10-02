"""Round-11 new-data-domain batch — declared in manifest.yaml
`round11_batch` BEFORE execution. Ten hypotheses on mechanisms only
testable after the 2026-09-23 data expansion: options vol surface,
liquidation cascades, mark-index basis, cross-venue funding aggregates,
on-chain stress/flow.

Input frame: harmony_extended.csv daily (t + 59 cols; c = btc_price).
Signal day d -> entry at close d -> eval close[d+horizon]. Rolling
percentiles are trailing-PRIOR-day (shift(1)) to stay causal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates_round8 import _sig_events

PRIOR_WIN = 365          # trailing percentile window (days)
PRIOR_MIN = 250          # min_periods — lets shorter columns start sooner


def _prior_q(s: pd.Series, q: float, win: int = PRIOR_WIN,
             min_p: int = PRIOR_MIN) -> np.ndarray:
    return (s.shift(1).rolling(win, min_periods=min_p)
            .quantile(q).to_numpy())


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(df.set_index("t")[name], errors="coerce")


def _pcol(df: pd.DataFrame, name: str) -> pd.Series:
    """Publish-lagged column read. External daily metrics are stamped for
    the day they describe but publish on d+1 (BGeometrics ~12:00Z,
    CheckOnChain similar). Entry is the close of day d = ~00:00Z d+1, so
    at the modeled instant only rows <= d-1 are public — signal legs read
    one day back (2026-09-25 publish-lag audit). _prior_q stays causal on
    top of this."""
    return _col(df, name).shift(1)


# ── OPTIONS-VOL ──────────────────────────────────────────────────────────

def dvol_spike_bounce_1d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """dvol 1d change >= prior p90 -> LONG +1d."""
    d = _pcol(df, "dvol_close").diff()
    thr = _prior_q(d, 0.90)
    sig = np.where(d.to_numpy() >= thr, 1.0, 0.0)
    sig[~(np.isfinite(d) & np.isfinite(thr))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)


def skew_extreme_reversal_3d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """skew25_1m <= p10 -> LONG +3d; >= p90 -> SHORT +3d."""
    sk = _pcol(df, "skew25_1m").to_numpy()
    lo, hi = _prior_q(pd.Series(sk), 0.10), _prior_q(pd.Series(sk), 0.90)
    sig = np.where(sk <= lo, 1.0, np.where(sk >= hi, -1.0, 0.0))
    sig[~(np.isfinite(sk) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=3, cooldown=3, asset=asset)


def iv_term_inversion_3d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """iv_atm_1w > iv_atm_3m -> LONG +3d."""
    s1 = _pcol(df, "iv_atm_1w").to_numpy()
    s3 = _pcol(df, "iv_atm_3m").to_numpy()
    inv = np.isfinite(s1) & np.isfinite(s3) & (s1 > s3)
    sig = np.where(inv, 1.0, 0.0)
    sig[~(np.isfinite(s1) & np.isfinite(s3))] = np.nan
    return _sig_events(df, sig, horizon=3, cooldown=3, asset=asset)


# ── LIQUIDATION ──────────────────────────────────────────────────────────

def liq_cascade_cont_1d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """liq total >= prior p90 -> dir=sign(day ret), +1d.
    liq_total_archive is truncated (2026-03+ only); liq_long+liq_short
    is the same total from the full 2022-12+ lineage — declared
    lineage substitution, not a spec change."""
    liq = (_pcol(df, "liq_long_usd").fillna(0)
           + _pcol(df, "liq_short_usd").fillna(0))
    liq = liq.where(_pcol(df, "liq_long_usd").notna())
    thr = _prior_q(liq, 0.90)
    ret = _col(df, "c").pct_change().to_numpy()
    l, th = liq.to_numpy(), thr
    sig = np.where(l >= th, np.sign(ret), 0.0)
    sig[~(np.isfinite(l) & np.isfinite(th) & np.isfinite(ret))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)


def liq_flush_bounce_1d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """liq_long_usd >= prior p90 (longs flushed) -> LONG +1d."""
    liq = _pcol(df, "liq_long_usd")
    thr = _prior_q(liq, 0.90)
    l, th = liq.to_numpy(), thr
    sig = np.where(l >= th, 1.0, 0.0)
    sig[~(np.isfinite(l) & np.isfinite(th))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)


# ── BASIS-CONVERGENCE ────────────────────────────────────────────────────

def premium_basis_converge_1d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """df merged: c = perp daily close, prem = premiumIndex daily close.
    |prem| >= prior p90 -> dir = -sign(prem), +1d."""
    prem = pd.to_numeric(df["prem"], errors="coerce").to_numpy()
    thr = _prior_q(pd.Series(np.abs(prem)), 0.90)
    sig = np.where(np.abs(prem) >= thr, -np.sign(prem), 0.0)
    sig[~(np.isfinite(prem) & np.isfinite(thr))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)


# ── XVENUE-FUNDING ───────────────────────────────────────────────────────

def funding_consensus_drift_1d(df: pd.DataFrame, asset: str
                               ) -> pd.DataFrame:
    """funding_agg_archive 3d-sum extreme -> drift direction, +1d."""
    f3 = _pcol(df, "funding_agg_archive").rolling(3).sum()
    lo = _prior_q(f3, 0.10)
    hi = _prior_q(f3, 0.90)
    f = f3.to_numpy()
    sig = np.where(f >= hi, 1.0, np.where(f <= lo, -1.0, 0.0))
    sig[~(np.isfinite(f) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)


# ── ONCHAIN-STRESS / ONCHAIN-FLOW ────────────────────────────────────────

def lth_sopr_capitulation_7d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """lth_sopr <= prior p10 -> LONG +7d (old hands' loss-taking = bottom)."""
    s = _pcol(df, "lth_sopr")
    lo = _prior_q(s, 0.10)
    sv, lv = s.to_numpy(), lo
    sig = np.where(sv <= lv, 1.0, 0.0)
    sig[~(np.isfinite(sv) & np.isfinite(lv))] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)


def nrpl_spike_top_3d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """nrpl_usd >= prior p90 -> SHORT +3d (realization spike = top)."""
    n = _pcol(df, "nrpl_usd")
    thr = _prior_q(n, 0.90)
    nv, th = n.to_numpy(), thr
    sig = np.where(nv > th, -1.0, 0.0)
    # strict > : a frozen/fingerprinted series yields th=0 and nv=0 —
    # 0>=0 would mint signals on dead data
    sig[~(np.isfinite(nv) & np.isfinite(th) & (th != 0))] = np.nan
    return _sig_events(df, sig, horizon=3, cooldown=3, asset=asset)


def exchange_balance_drift_7d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """balance 7d change <= p10 -> LONG +7d; >= p90 -> SHORT +7d."""
    d7 = _pcol(df, "exchange_balance_total").diff(7)
    lo = _prior_q(d7, 0.10)
    hi = _prior_q(d7, 0.90)
    d = d7.to_numpy()
    sig = np.where(d < lo, 1.0, np.where(d > hi, -1.0, 0.0))
    # lo<hi required: the fingerprinted/frozen exchange_balance segment
    # (2011-2013, upstream placeholder) yields lo==hi==0 and d==0 —
    # strict inequalities alone still let a nonzero wiggle fire on a
    # dead series
    sig[~(np.isfinite(d) & np.isfinite(lo) & np.isfinite(hi)
          & (lo < hi))] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)
