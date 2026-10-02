"""Round-12 remaining-columns batch — declared in manifest.yaml
`round12_batch` BEFORE execution. Ten hypotheses on the last untested
harmony_extended columns: CME OI (institutional positioning), venue
premia (coinbase/bybit), dormancy/CDD, miner economics (puell), cycle
valuation (reserve_risk, lth_mvrv), STH capitulation, nrpl loss side,
cross-venue funding spread.

Same event contract: signal day d -> entry close d -> eval close[d+h].
Rolling percentiles are trailing-prior-day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from harness.candidates_round11 import _col, _pcol, _prior_q
from harness.candidates_round8 import _sig_events


def _ret(df: pd.DataFrame, days: int = 1) -> np.ndarray:
    return _col(df, "c").pct_change(days).to_numpy()


# ── CME-POSITIONING ──────────────────────────────────────────────────────

def cme_oi_confirm_3d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """cme OI 7d change >= prior p90 -> dir=sign(7d px ret), +3d."""
    doi = _pcol(df, "oi_futures_cme").pct_change(7)
    thr = _prior_q(doi, 0.90)
    r7 = _ret(df, 7)
    d, th = doi.to_numpy(), thr
    sig = np.where(d >= th, np.sign(r7), 0.0)
    sig[~(np.isfinite(d) & np.isfinite(th) & np.isfinite(r7))] = np.nan
    return _sig_events(df, sig, horizon=3, cooldown=3, asset=asset)


# ── VENUE-PREMIUM ────────────────────────────────────────────────────────

def _premium_drift(df: pd.DataFrame, asset: str, col: str,
                   ) -> pd.DataFrame:
    p = _pcol(df, col)
    lo, hi = _prior_q(p, 0.10), _prior_q(p, 0.90)
    pv = p.to_numpy()
    sig = np.where(pv >= hi, 1.0, np.where(pv <= lo, -1.0, 0.0))
    sig[~(np.isfinite(pv) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)


def coinbase_premium_drift_1d(df: pd.DataFrame, asset: str
                              ) -> pd.DataFrame:
    return _premium_drift(df, asset, "coinbase_premium")


def bybit_premium_drift_1d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    return _premium_drift(df, asset, "bybit_premium")


# ── ONCHAIN-FLOW / ONCHAIN-STRESS ────────────────────────────────────────

def dormancy_spike_fade_7d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """cdd 7d-sum >= prior p90 -> SHORT +7d (old coins moving)."""
    c7 = _pcol(df, "cdd").rolling(7).sum()
    thr = _prior_q(c7, 0.90)
    c, th = c7.to_numpy(), thr
    sig = np.where(c >= th, -1.0, 0.0)
    sig[~(np.isfinite(c) & np.isfinite(th))] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)


def sth_sopr_loss_bounce_3d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """sth_sopr <= prior p10 -> LONG +3d."""
    s = _pcol(df, "sth_sopr")
    lo = _prior_q(s, 0.10)
    sv, lv = s.to_numpy(), lo
    sig = np.where(sv <= lv, 1.0, 0.0)
    sig[~(np.isfinite(sv) & np.isfinite(lv))] = np.nan
    return _sig_events(df, sig, horizon=3, cooldown=3, asset=asset)


def nrpl_capitulation_3d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """nrpl_usd <= prior p10 (mass loss-realization) -> LONG +3d."""
    n = _pcol(df, "nrpl_usd")
    lo = _prior_q(n, 0.10)
    nv, lv = n.to_numpy(), lo
    sig = np.where(nv <= lv, 1.0, 0.0)
    sig[~(np.isfinite(nv) & np.isfinite(lv))] = np.nan
    return _sig_events(df, sig, horizon=3, cooldown=3, asset=asset)


# ── MINER-ECON / CYCLE-VALUATION ─────────────────────────────────────────

def puell_extreme_7d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """puell >= p90 -> SHORT +7d; <= p10 -> LONG +7d."""
    p = _pcol(df, "puell")
    lo, hi = _prior_q(p, 0.10), _prior_q(p, 0.90)
    pv = p.to_numpy()
    sig = np.where(pv >= hi, -1.0, np.where(pv <= lo, 1.0, 0.0))
    sig[~(np.isfinite(pv) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)


def reserve_risk_regime_7d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """reserve_risk <= p10 -> LONG +7d; >= p90 -> SHORT +7d."""
    r = _pcol(df, "reserve_risk")
    lo, hi = _prior_q(r, 0.10), _prior_q(r, 0.90)
    rv = r.to_numpy()
    sig = np.where(rv <= lo, 1.0, np.where(rv >= hi, -1.0, 0.0))
    sig[~(np.isfinite(rv) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)


def lth_mvrv_extreme_7d(df: pd.DataFrame, asset: str) -> pd.DataFrame:
    """lth_mvrv >= p90 -> SHORT +7d; <= p10 -> LONG +7d."""
    m = _pcol(df, "lth_mvrv")
    lo, hi = _prior_q(m, 0.10), _prior_q(m, 0.90)
    mv = m.to_numpy()
    sig = np.where(mv >= hi, -1.0, np.where(mv <= lo, 1.0, 0.0))
    sig[~(np.isfinite(mv) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=7, cooldown=7, asset=asset)


# ── XVENUE-FUNDING ───────────────────────────────────────────────────────

def xvenue_funding_spread_1d(df: pd.DataFrame, asset: str
                             ) -> pd.DataFrame:
    """(funding_binance_um - funding_bybit) 3d-sum extreme -> fade
    the froth side: >= p90 SHORT +1d; <= p10 LONG +1d."""
    spr = (_pcol(df, "funding_binance_um")
           - _pcol(df, "funding_bybit")).rolling(3).sum()
    lo, hi = _prior_q(spr, 0.10), _prior_q(spr, 0.90)
    sv = spr.to_numpy()
    sig = np.where(sv >= hi, -1.0, np.where(sv <= lo, 1.0, 0.0))
    sig[~(np.isfinite(sv) & np.isfinite(lo) & np.isfinite(hi))] = np.nan
    return _sig_events(df, sig, horizon=1, cooldown=1, asset=asset)
