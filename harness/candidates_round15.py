"""Round-15 — LIVE-UNUSED-COLUMNS batch. Declared in manifest
`round15_batch` BEFORE execution.

Five hypotheses on the last economically distinct LIVE inputs never
consumed by any emitter (coverage audit 2026-09-28: 39 never-consumed
columns, of which these are live with meaningful history):

  dormancy           — coin-age velocity (old-coin distribution spikes)
  hashrate           — miner capitulation drawdowns ("hash ribbon")
  fred_us10y         — rates-shock liquidity drain
  realized_pl_ratio  — realized loss-dominance capitulation gauge
  sth_mvrv           — short-term-holder cost-basis capitulation

Family billing: dormancy variant is a sibling of the killed cdd-spike
fade (R12); realized_pl_ratio / sth_mvrv are siblings of the
sopr-bounce / mvrv families — billed to those families, not new.
hashrate and us10y are new families.

Same event contract: signal day d -> entry close d -> eval close[d+h].
Inputs publish-lagged (_pcol); percentiles trailing-prior-day
(_prior_q); single-threshold fires additionally require the p10<p90
window to be non-degenerate (A32 flat-data guard class).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates_round11 import _pcol, _prior_q
from harness.candidates_round8 import _sig_events


def dormancy_spike_short_7d(df: pd.DataFrame, asset: str
                            ) -> pd.DataFrame:
    """dormancy >= prior p90 -> SHORT +7d (old coins moving =
    distribution overhang). Live-metric sibling of the killed
    cdd-based dormancy_spike_fade_7d."""
    d = _pcol(df, "dormancy")
    lo, hi = _prior_q(d, 0.10), _prior_q(d, 0.90)
    dv = d.to_numpy()
    ok = np.isfinite(dv) & np.isfinite(lo) & np.isfinite(hi) & (lo < hi)
    sig = np.where(dv >= hi, -1.0, 0.0)
    sig[~ok] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)


def hashrate_drawdown_long_14d(df: pd.DataFrame, asset: str
                               ) -> pd.DataFrame:
    """hashrate 30d change <= prior p10 -> LONG +14d (miner
    capitulation marks accumulation zones — hash-ribbon mechanism)."""
    h30 = _pcol(df, "hashrate").pct_change(30)
    lo, hi = _prior_q(h30, 0.10), _prior_q(h30, 0.90)
    hv = h30.to_numpy()
    ok = np.isfinite(hv) & np.isfinite(lo) & np.isfinite(hi) & (lo < hi)
    sig = np.where(hv <= lo, 1.0, 0.0)
    sig[~ok] = np.nan
    return _sig_events(df, sig, horizon=14, cooldown=14, asset=asset)


def us10y_shock_short_5d(df: pd.DataFrame, asset: str
                         ) -> pd.DataFrame:
    """fred_us10y 5d z >= +2 -> SHORT +5d (rates shock drains risk
    liquidity; rates-side twin of the equity-lead risk-off short).
    us10y is a business-day series (~32% NaN on the daily spine): the
    publish-lagged read is ffilled so diff(5) measures the 5-calendar-
    day change in the last published yield — PIT-safe (only carries
    already-public values forward)."""
    u = _pcol(df, "fred_us10y").ffill()
    d5 = u.diff(5)
    r = d5.rolling(252, min_periods=120)
    z = ((d5 - r.mean()) / r.std()).to_numpy()
    sig = np.where(z >= 2.0, -1.0, 0.0)
    sig[~np.isfinite(z)] = np.nan
    return _sig_events(df, sig, horizon=5, cooldown=5, asset=asset)


def realized_pl_ratio_capitulation_5d(df: pd.DataFrame, asset: str
                                      ) -> pd.DataFrame:
    """realized_pl_ratio <= prior p10 -> LONG +5d (realized losses
    dominating profits = capitulation exhaustion)."""
    p = _pcol(df, "realized_pl_ratio")
    lo, hi = _prior_q(p, 0.10), _prior_q(p, 0.90)
    pv = p.to_numpy()
    ok = np.isfinite(pv) & np.isfinite(lo) & np.isfinite(hi) & (lo < hi)
    sig = np.where(pv <= lo, 1.0, 0.0)
    sig[~ok] = np.nan
    return _sig_events(df, sig, horizon=5, cooldown=5, asset=asset)


def sth_mvrv_capitulation_7d(df: pd.DataFrame, asset: str
                             ) -> pd.DataFrame:
    """sth_mvrv <= prior p10 -> LONG +7d (short-term holders
    underwater on cost basis = weakest hands flushed)."""
    m = _pcol(df, "sth_mvrv")
    lo, hi = _prior_q(m, 0.10), _prior_q(m, 0.90)
    mv = m.to_numpy()
    ok = np.isfinite(mv) & np.isfinite(lo) & np.isfinite(hi) & (lo < hi)
    sig = np.where(mv <= lo, 1.0, 0.0)
    sig[~ok] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)
